# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import json
import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from pprint import pformat
from vakt import Policy, Inquiry, Guard, RulesChecker, ALLOW_ACCESS, DENY_ACCESS
from vakt.exceptions import PolicyExistsError
from vakt.rules import CIDR, Any, Eq, NotEq, In, StartsWith, RegexMatch

from .models import Policy as DjPolicy
from .storage import DjangoStorage

# Create your tests here.
class PolicyTests(TestCase):
    def setUp(self):
        self.storage = DjangoStorage()
        self.guard = Guard(self.storage, RulesChecker())

        self.policy1 = Policy(
            uuid.uuid4(),
            actions=[Eq('get'), Eq('list'), Eq('read')],
            resources=[StartsWith('repos/google/tensor')],
            subjects=[{'name': Any(), 'role': Any()}],
            context={ 'module': Eq('Test') },
            effect=ALLOW_ACCESS,
            description='Grant read-access for all Google repositories starting with "tensor" to any User'
        )

        self.policy2 = Policy(
            uuid.uuid4(),
            actions=[In('delete', 'prune', 'exterminate')],
            resources=[StartsWith('repos/')],
            subjects=[{'name': Any(), 'role': Eq('admin')}],
            context={ 'module': Eq('Test') },
            effect=ALLOW_ACCESS,
            description='Grant admin access'
        )

    def test_crud(self):
        ## Create (add)
        self.storage.add(self.policy1)

        # try to add it again, it should raise a exception
        try:
            self.storage.add(self.policy1)
            raise Exception("The DjangoStorage should't store a policy more than once")
        except PolicyExistsError:
            pass

        ## Read
        # get
        test_policy = self.storage.get(self.policy1.uid)
        assert test_policy, "The storage doesn't return a policy from get"
        assert self.policy1.uid == test_policy.uid, "These policies must be equal"

        must_be_none = self.storage.get(self.policy2.uid)
        assert not must_be_none, "This policy shouldn't exists"

        # get all
        self.storage.add(self.policy2)
        test_policies = self.storage.get_all()

        assert test_policies, "This should return a policies list"
        assert test_policies[0].uid == self.policy1.uid \
            and test_policies[1].uid == self.policy2.uid,\
            "The returned list should match"

        ## Update
        policy1b = Policy(
            self.policy1.uid,
            actions=[Eq('get'), Eq('list')],
            resources=[{'category': Eq('administration'), 'sub': In('panel', 'switch')}],
            subjects=[{'name': Any(), 'role': NotEq('developer')}],
            effect=ALLOW_ACCESS,
            context={ 'module': Eq('Test') },
            description="""
            Allow access to administration interface subcategories: 'panel', 'switch' if user is not
            a developer and came from local IP address.
            """
        )
        self.storage.update(policy1b)
        test_policy = self.storage.get(self.policy1.uid)
        assert self.policy1.uid == test_policy.uid and\
            test_policy.to_json() == policy1b.to_json(),\
            "The test policy values doesn't match with the updated version"

        ## Delete
        self.storage.delete(self.policy2.uid)
        test_policies = self.storage.get_all()

        test_none = self.storage.get(self.policy2.uid)
        assert not test_none, "This policy shouldn't be stored as it has been deleted"

        assert len(test_policies) == 1 and test_policies[0].uid == self.policy1.uid, \
            "The returned list should match"

        ## Find for inquiry
        # check a matching policy
        inquiry1 = Inquiry(
            action='get',
            resource='repos/foo/bar',
            subject={ 'name': 'Jane', 'role': 'admin'},
            context={'module': 'Test'}
        )
        matching_policies = self.storage.find_for_inquiry(inquiry1, self.guard.checker)
        assert matching_policies, "The matching policies list should be empty"

        # check it doesn't match and inquiry
        inquiry2 = Inquiry(
            action='delete',
            resource='repos/google/tensorflow',
            subject={ 'name': 'Max', 'role': 'developer'},
            context={'module': 'Test'}
        )
        matching_policies = self.storage.find_for_inquiry(inquiry2, self.guard.checker)
        assert not matching_policies, "The matching policies list should be empty"
