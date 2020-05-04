# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from djangovakt.models import Policy as DjPolicy
from vakt import Policy, RulesChecker
from vakt.storage.abc import Storage
from vakt.exceptions import PolicyExistsError

import json
import logging
import threading
import vakt.rules

log = logging.getLogger(__name__)

class DjangoStorage(Storage):
    def __init__(self, djpolicy_model=None):
        self.lock = threading.Lock()
        if not djpolicy_model:
            djpolicy_model = DjPolicy

        self.djpolicy = djpolicy_model

    def add(self, policy):
        uid = policy.uid

        # check if it's already stored and raise exception if so
        existent_policy = self.djpolicy.objects.filter(uid=uid)
        if existent_policy:
            raise PolicyExistsError(policy.uid)

        # add policy
        djpolicy = DjangoStorage.__prepare_djmodel(policy, self.djpolicy)
        djpolicy.save()

        log.info('Added Policy: %s \n', policy)

    def get(self, uid):
        try:
            return DjangoStorage.__prepare_from_djmodel(self.djpolicy.objects.get(uid=uid))
        except ObjectDoesNotExist:
            return None

    def get_all(self, limit=0, offset=0):
        self._check_limit_and_offset(limit, offset)
        count = self.djpolicy.objects.count()

        if offset > count:
            return []

        if limit == 0:
            limit = count

        qs = self.djpolicy.objects.all()[offset:offset+limit]
        all_policies = [ DjangoStorage.__prepare_from_djmodel(djpol) for djpol in qs ]
        log.debug('Get all policies: {}\n'.format(all_policies))
        return all_policies

    def find_for_inquiry(self, inquiry, checker=None):
        # worst case return all
        qs = self.djpolicy.objects.all()

        if isinstance(checker, RulesChecker):
            # extract action, context, resource and subject from inquiry
            inquiry_resource = inquiry.resource
            inquiry_action = inquiry.action
            inquiry_subject = inquiry.subject
            inquiry_context = inquiry.context
            
            # filter by action name
            qs = qs.filter(doc__actions__0__val=inquiry_action)
            qs = qs.filter(doc__context__module__elem__in=inquiry_context['module'])

        policies = [ DjangoStorage.__prepare_from_djmodel(djpol) for djpol in qs ]
        log.debug('Find for inquiry: {}\n Return matching policies: {}\n'.format(
            inquiry, policies
        ))

        return policies

    def update(self, policy):
        # we could store directly the djpolicy either way
        dbpolicy = self.djpolicy.objects.get(uid=policy.uid)
        newdjpolicy = DjangoStorage.__prepare_djmodel(policy, self.djpolicy)
        dbpolicy.doc = newdjpolicy.doc
        dbpolicy.save()
        log.info('Updated Policy with UID=%s. New value is: %s\n', policy.uid, policy)

    def delete(self, uid):
        dbpolicy = self.djpolicy.objects.get(uid=uid)
        dbpolicy.delete()
        log.info('Deleted Policy with UID %s\n', uid)

    @staticmethod
    def __prepare_djmodel(policy, djpolicy):
        """
        Prepare Policy object as a document for insertion.
        """
        policy_jstring = policy.to_json()
        djpolicy = djpolicy(uid=policy.uid, doc=policy_jstring)

        return djpolicy

    @staticmethod
    def __prepare_from_djmodel(djmodel):
        """
        Prepare Policy object as a return from a JSONField.
        """

        return Policy.from_json(djmodel.doc)
