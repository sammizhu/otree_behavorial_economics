from otree.api import Page
from .models import Constants, Case
import json
import random

class ArrivalPage(Page):
    def is_displayed(self):
        # Simulate judge arrival; judges arrive randomly
        self.player.arrived = True
        return True  # Always display to update arrival status

    def vars_for_template(self):
        # Fetch unassigned cases for the current subsession
        cases = Case.filter(subsession=self.subsession, is_assigned=False)

        # Include round number in context for debugging and display
        return {
            'cases': cases,  # Pass the unassigned cases to the template
            'arrived': self.player.arrived,
            'round_number': self.subsession.round_number
        }


class SelectCasesPage(Page):
    form_model = 'player'
    form_fields = ['selected_case_ids']

    def is_displayed(self):
        # Only display if the judge has arrived
        return self.player.arrived

    def vars_for_template(self):
        # Use session vars to filter available cases
        available_case_ids = self.session.vars.get('cases', [])
        # Fetch only cases matching the specified IDs and not assigned
        cases =  cases = Case.filter(subsession=self.subsession, is_assigned=False)

        # Convert to a list of dictionaries for compatibility with the HTML template
        case_list = [{'id': case.id, 'case_id': case.case_id, 'points': case.points} for case in cases]

        return {
            'cases': case_list,
            'round_number': self.subsession.round_number,
            'arrived': self.player.arrived
        }

    def before_next_page(self):
        # Safely check if `selected_case_ids` is not None and not an empty string
        if self.player.selected_case_ids is not None and self.player.selected_case_ids != '':
            chosen_case_ids = [int(cid) for cid in json.loads(self.player.selected_case_ids)]
            # Use `Case.id.in_(chosen_case_ids)` for filtering
            for case in Case.objects_filter(subsession=self.subsession).filter(Case.id.in_(chosen_case_ids)):
                case.is_assigned = True
                case.save()
            # Remove assigned cases from the available cases list
            self.session.vars['cases'] = [
                cid for cid in self.session.vars['cases']
                if cid not in chosen_case_ids
            ]
        else:
            self.player.selected_case_ids = json.dumps([])  # Set an empty list as default if not set


class ResultsPage(Page):
    def is_displayed(self):
        return self.player.arrived

    def vars_for_template(self):
        # Load selected cases
        selected_case_ids = json.loads(self.player.selected_case_ids or '[]')
        selected_cases = [Case.get(subsession=self.subsession, id=int(case_id)) for case_id in selected_case_ids]
        return {
            'selected_cases': selected_cases,
            'round_number': self.subsession.round_number,
            'arrived': self.player.arrived
        }

# Define the sequence of pages for the app
page_sequence = [
    ArrivalPage,
    SelectCasesPage,
    ResultsPage
]