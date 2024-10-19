from otree.api import Page
from .models import Constants, Case, Judge
import json
import random

class ArrivalPage(Page):
    def is_displayed(self):
        # Simulate judge arrival; judges arrive randomly
        self.player.arrived = True
        return True  # Always display to update arrival status

    def vars_for_template(self):
        # Fetch unassigned cases for the current session
        cases = Case.filter(session=self.session, is_assigned=False)

        return {
            'cases': cases,
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
        # Fetch unassigned cases for the current session
        cases = Case.filter(session=self.session, is_assigned=False)
        # Convert to a list of dictionaries for the template
        case_list = [{'id': case.id, 'case_id': case.case_id, 'points': case.points} for case in cases]

        return {
            'cases': case_list,
            'round_number': self.subsession.round_number,
            'arrived': self.player.arrived
        }


    def before_next_page(self):
            # Print raw form data to debug
            raw_data = self._form_data.getlist('selected_case_ids[]')
            self.player.selected_case_ids = json.dumps(raw_data)
            self.player.selected_cases_list = [int(case_id) for case_id in raw_data]
            
            # Check if `selected_case_ids` is not None and not an empty string
            if self.player.selected_case_ids and self.player.selected_case_ids != '':
                # Ensure the string is in a JSON array format
                if not self.player.selected_case_ids.startswith("["):
                    self.player.selected_case_ids = f'["{self.player.selected_case_ids}"]'

                # Convert the JSON string to a list of case IDs
                self.player.selected_cases_list = [int(cid) for cid in json.loads(self.player.selected_case_ids)]

                # Fetch the current judge for this player
                current_judge_list = Judge.filter(session=self.session, player=self.player)
                current_judge = current_judge_list[0] if current_judge_list else None

                # Assign the selected cases to this judge
                for case_id in self.player.selected_cases_list:
                    # Use the first element from the filter result
                    case = Case.filter(session=self.session, id=case_id)[0]
                    case.is_assigned = True
                    case.judge = current_judge

                # Remove assigned cases from the session list
                self.session.vars['cases'] = [cid for cid in self.session.vars['cases'] if cid not in self.player.selected_cases_list]
            else:
                self.player.selected_cases_list = [] 

class ResultsPage(Page):
    def is_displayed(self):
        return self.player.arrived

    def vars_for_template(self):
        # Retrieve the judge associated with the current player
        all_cases = Case.filter(session=self.session)

        current_judges = Judge.filter(session=self.session, player=self.player)
        if current_judges:
            current_judge = current_judges[0]
        else:
            current_judge = None

        if not current_judge:
            return {
                'selected_cases': [],
                'round_number': self.subsession.round_number,
                'arrived': self.player.arrived
            }

        # Fetch cases assigned to this specific judge
        selected_cases = Case.filter(session=self.session, judge=current_judge)

        # Convert the cases to a list of dictionaries for compatibility with HTML templates
        case_list = [
            {'id': case.id, 'case_id': case.case_id, 'points': case.points, 'judge_id': case.judge.judge_id}
            for case in selected_cases
        ]

        return {
            'all_cases': all_cases,
            'judge': current_judge,
            'selected_cases': case_list,
            'round_number': self.subsession.round_number,
            'arrived': self.player.arrived
        }

# Define the sequence of pages for the app
page_sequence = [
    ArrivalPage,
    SelectCasesPage,
    ResultsPage
]