# -*- coding: utf-8 -*-
__author__ = 'ffuentes'

import json
import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.test import TestCase
from pprint import pformat
from vakt import Policy, Inquiry, Guard, RulesChecker, ALLOW_ACCESS, DENY_ACCESS
from vakt.exceptions import PolicyExistsError
import vakt.rules as vrules

from .models import Policy as DjPolicy
from .storage import DjangoStorage

# Create your tests here.
class PolicyTests(TestCase):
    def setUp(self):
        self.storage = DjangoStorage()
        self.guard = Guard(self.storage, RulesChecker())

    def test_crud(self):
        for dbpolicy in self.storage.get_all():
            self.storage.delete(dbpolicy.uid)

        # create policies
        self.policy1 = Policy(
            uuid.uuid4(),
            actions=[vrules.In('get', 'list', 'read')],
            resources=[vrules.StartsWith('repos/google/tensor')],
            subjects=[{'name': vrules.Any(), 'role': vrules.Any()}],
            context={ 'module': vrules.Eq('Test') },
            effect=ALLOW_ACCESS,
            description='Grant read-access for all Google repositories starting with "tensor" to any User'
        )

        self.policy2 = Policy(
            uuid.uuid4(),
            actions=[vrules.In('delete', 'prune', 'exterminate')],
            resources=[vrules.StartsWith('repos/')],
            subjects=[{'name': vrules.Any(), 'role': vrules.Eq('admin')}],
            context={ 'module': vrules.Eq('Test') },
            effect=ALLOW_ACCESS,
            description='Grant admin access'
        )

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
            actions=[vrules.In('get', 'list')],
            resources=[{'category': vrules.Eq('administration'), 'sub': vrules.In('panel', 'switch')}],
            subjects=[{'name': vrules.Any(), 'role': vrules.NotEq('developer')}],
            effect=ALLOW_ACCESS,
            context={ 'module': vrules.Eq('Test') },
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
            resource='repos/google/tensorflow',
            subject={ 'name': 'Jane', 'role': 'admin'},
            context={'module': 'Test'}
        )
        matching_policies = self.storage.find_for_inquiry(inquiry1, self.guard.checker)
        assert matching_policies, "The matching policies list should not be empty"

        # check it doesn't match and inquiry
        inquiry2 = Inquiry(
            action='delete',
            resource='repos/google/tensorflow',
            subject={ 'name': 'Max', 'role': 'developer'},
            context={'module': 'Test'}
        )
        matching_policies = self.storage.find_for_inquiry(inquiry2, self.guard.checker)
        assert not matching_policies, "The matching policies list should be empty"

    def test_rulechecker(self):
        # ensure empty policy set
        for dbpolicy in self.storage.get_all():
            self.storage.delete(dbpolicy.uid)

        # add policies
        policy1 = Policy(
            uuid.uuid4(),
            actions=[vrules.Eq('read')],
            resources=[vrules.StartsWith('forum/')],
            subjects=[{ 'group': vrules.In('can_read', 'can_write', 'can_admin') }],
            context={ 'module': vrules.Eq('forum') },
            effect=ALLOW_ACCESS,
            description='Grant read-access to the forum section to users with a certain profile'
        )

        policy2 = Policy(
            uuid.uuid4(),
            actions=[vrules.Eq('write')],
            resources=[vrules.StartsWith('forum/')],
            subjects=[{ 'group': vrules.In('can_write', 'can_admin') }],
            context={ 'module': vrules.Eq('forum') },
            effect=ALLOW_ACCESS,
            description='Grant write-access to the forum section to users with a certain profile'
        )

        policy3 = Policy(
            uuid.uuid4(),
            actions=[vrules.Eq('admin')],
            resources=[vrules.StartsWith('forum/')],
            subjects=[{ 'group': vrules.In('can_admin') }],
            context={ 'module': vrules.Eq('forum') },
            effect=ALLOW_ACCESS,
            description='Grant admin-access to the forum section to users with a certain profile'
        )

        policy4 = Policy(
            uuid.uuid4(),
            actions=[vrules.Any()],
            resources=[vrules.StartsWith('forum/')],
            subjects=[{ 'group': vrules.NotIn('can_read', 'can_write', 'can_admin') }],
            context={ 'module': vrules.Eq('forum') },
            effect=DENY_ACCESS,
            description='Deny access to any user without a group defined'
        )


        self.storage.add(policy1)
        self.storage.add(policy2)
        self.storage.add(policy3)
        self.storage.add(policy4)

        # forge successful inquiry for 1st policy
        inqu1_ok = Inquiry(
            action='read',
            resource='forum/users/list',
            subject={ 'name': 'Jane', 'group': 'can_read'},
            context={'module': 'forum'}
        )

        assert self.guard.is_allowed(inqu1_ok), "This inquiry should be allowed"

        inq1_ko = Inquiry(
            action='read',
            resource='forum/users/list',
            subject={ 'name': 'James', 'group': 'new_users'},
            context={'module': 'forum'}
        )

        assert not self.guard.is_allowed(inq1_ko), "This inquiry should be denied"
