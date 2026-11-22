import unittest

from scripts.verify_role_dispatch import assess


class DispatchCanaryTests(unittest.TestCase):
    def test_dispatch_requires_typed_lifecycle_and_child_evidence(self):
        def item(thread, **data):
            return {'method': 'item/completed', 'params': {'threadId': thread, 'item': data}}

        parent, child, marker = 'parent', 'child', 'fixture-marker'
        spawn = item(parent, type='subAgentActivity', kind='started', agentThreadId=child)
        complete = item(parent, type='subAgentActivity', kind='completed', agentThreadId=child)
        text = f'{marker}: sample.py:4 calls convert at bridge.py:1'
        child_output = item(child, type='agentMessage', phase='final_answer', text=text)
        parent_output = item(parent, type='agentMessage', phase='final_answer',
                             text='sample.py:4 calls convert at bridge.py:1')
        self.assertTrue(all(assess([spawn, complete, child_output, parent_output], parent, marker).values()))
        self.assertFalse(assess([parent_output], parent, marker)['dispatch_observed'])
        self.assertFalse(assess([spawn, complete, parent_output], parent, marker)['child_evidence_matches'])
        self.assertFalse(assess([spawn, child_output, parent_output], parent, marker)['child_completed'])
        self.assertFalse(assess([spawn, parent_output, child_output, complete], parent, marker)['parent_handoff_matches'])
        extra = item(parent, type='subAgentActivity', kind='started', agentThreadId='extra')
        self.assertFalse(assess([spawn, complete, child_output, parent_output, extra], parent, marker)['dispatch_observed'])
