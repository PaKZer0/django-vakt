# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import threading
import logging
import vakt.rules

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from djangovakt.models import Policy as DjPolicy
from vakt import Policy, RulesChecker
from vakt.storage.abc import Storage
from vakt.exceptions import PolicyExistsError

log = logging.getLogger(__name__)

class DjangoStorage(Storage):
    def __init__(self):
        self.lock = threading.Lock()

    def add(self, policy):
        uid = policy.uid

        # check if it's already stored and raise exception if so
        existent_policy = DjPolicy.objects.filter(uid=uid)
        if existent_policy:
            raise PolicyExistsError(policy.uid)

        # add policy
        djpolicy = DjangoStorage.__prepare_djmodel(policy)
        djpolicy.save()

        log.info('Added Policy: %s', policy)

    def get(self, uid):
        try:
            return DjangoStorage.__prepare_from_djmodel(DjPolicy.objects.get(uid=uid))
        except ObjectDoesNotExist:
            return None

    def get_all(self, limit=0, offset=0):
        self._check_limit_and_offset(limit, offset)
        count = DjPolicy.objects.count()

        if offset > count:
            return []

        if limit == 0:
            limit = count

        qs = DjPolicy.objects.all()[offset:offset+limit]

        return [ DjangoStorage.__prepare_from_djmodel(djpol) for djpol in qs ]

    def find_for_inquiry(self, inquiry, checker=None):
        # worst case return all
        qs = DjPolicy.objects.all()

        if isinstance(checker, RulesChecker):
            # extract action, context, resource and subject from inquiry
            inquiry_resource = inquiry.resource
            inquiry_action = inquiry.action
            inquiry_subject = inquiry.subject
            inquiry_context = inquiry.context

            # extract all action rules in dictionary with policy uuid
            match_policies_uids = []

            for dbpolicy in self.get_all():
                resource = dbpolicy.resource
                actions = dbpolicy.actions
                subject = dbpolicy.subject
                context = dbpolicy.context

                insert_uid = True

                # filter subject
                if insert_uid:
                    for rule in subject:
                        # if one of the rules doesn't fit remove uuid from matching_policies
                        if not rule.satisfied(inquiry_subject):
                            insert_uid = False

                # filter resource
                if insert_uid:
                    for rule in resource:
                        # if one of the rules doesn't fit remove uuid from matching_policies
                        if not rule.satisfied(inquiry_resource):
                            insert_uid = False

                # filter actions
                if insert_uid:
                    for rule in actions:
                        # if one of the rules doesn't fit remove uuid from matching_policies
                        if not rule.satisfied(inquiry_action):
                            insert_uid = False

                # filter context
                if insert_uid:
                    for rule in context:
                        # if one of the rules doesn't fit remove uuid from matching_policies
                        if not rule.satisfied(inquiry_context):
                            insert_uid = False

                if insert_uid:
                    match_policies_uids.append(dbpolicy.uid)

            # filter queryset using Q object list
            qs = DjPolicy.objects.filter(uid__in=match_policies_uids)

        return [ DjangoStorage.__prepare_from_djmodel(djpol) for djpol in qs ]

    def update(self, policy):
        # we could store directly the djpolicy either way
        dbpolicy = DjPolicy.objects.get(uid=policy.uid)
        djpolicy = DjangoStorage.__prepare_djmodel(policy)
        dbpolicy.doc = djpolicy.doc
        dbpolicy.save()
        log.info('Updated Policy with UID=%s. New value is: %s', policy.uid, policy)

    def delete(self, uid):
        dbpolicy = DjPolicy.objects.get(uid=uid)
        dbpolicy.delete()
        log.info('Policy with UID %s was deleted', uid)

    @staticmethod
    def __prepare_djmodel(policy):
        """
        Prepare Policy object as a document for insertion.
        """
        djpolicy = DjPolicy(uid=policy.uid, doc=policy.to_json())

        return djpolicy

    @staticmethod
    def __prepare_from_djmodel(djmodel):
        """
        Prepare Policy object as a return from a JSONField.
        """
        return Policy.from_json(djmodel.doc)
