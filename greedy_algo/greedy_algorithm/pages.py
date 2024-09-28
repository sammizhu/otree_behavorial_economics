# pages.py

from otree.api import Page, WaitPage
from .models import Constants, Case
import random
import json

class ArrivalPage(Page):
    def is_displayed(self):
        # Simulate judge arrival; judges arrive randomly
        arrived = random.choice([True, False])
        self.player.arrived = arrived
        return True  # Always display to update arrival status

    def vars_for_template(self):
        return {
            'arrived': self.player.arrived,
            'round_number': self.subsession.round_number
        }

class SelectCasesPage(Page):
    form_model = 'player'

    def is_displayed(self):
        return self.player.arrived

    def vars_for_template(self):
        # Get available (unassigned) cases
        case_ids = self.session.vars.get('cases', [])
        cases = [Case.get(id=case_id) for case_id in case_ids if not Case.get(id=case_id).is_assigned]
        return {
            'cases': cases
        }

    def before_next_page(self):
        selected_case_ids = self.request.POST.getlist('cases')
        if selected_case_ids:
            self.player.selected_case_ids = json.dumps(selected_case_ids)
            for case_id in selected_case_ids:
                case = Case.get(id=int(case_id))
                case.is_assigned = True
                case.save()
        else:
            self.player.selected_case_ids = json.dumps([])

class ResultsPage(Page):
    def is_displayed(self):
        return self.player.arrived

    def vars_for_template(self):
        selected_case_ids = json.loads(self.player.selected_case_ids or '[]')
        selected_cases = [Case.get(id=int(case_id)) for case_id in selected_case_ids]
        return {
            'selected_cases': selected_cases
        }

page_sequence = [
    ArrivalPage,
    SelectCasesPage,
    ResultsPage
]