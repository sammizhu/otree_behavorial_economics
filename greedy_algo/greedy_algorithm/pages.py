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
            # Check if `selected_case_ids` is not None and not an empty string
            if self.player.selected_case_ids is not None and self.player.selected_case_ids != '':
                # Ensure the string is in a JSON array format
                if not self.player.selected_case_ids.startswith("["):
                    # If not in array format, wrap it in square brackets
                    self.player.selected_case_ids = f"[{self.player.selected_case_ids}]"
                
                # Convert the JSON string to a list of case IDs
                self.player.selected_cases_list = [int(cid) for cid in json.loads(self.player.selected_case_ids)]
                print("HEREHERHEEHRER", self.player.selected_cases_list)
                # Fetch the current judge for this player
                current_judge_list = Judge.filter(subsession=self.subsession, player=self.player)
                current_judge = current_judge_list[0] if current_judge_list else None
                
                # Assign the selected cases to this judge
                for case_id in self.player.selected_cases_list:
                    case = Case.filter(subsession=self.subsession, id=case_id)[0]
                    print("blah blah", case)
                    case.is_assigned = True
                    case.judge = current_judge

                # Remove assigned cases from the session list
                self.session.vars['cases'] = [cid for cid in self.session.vars['cases'] if cid not in self.player.selected_cases_list]
            else:
                self.player.selected_cases_list = []  # Set an empty list if no cases are s

class ResultsPage(Page):
    def is_displayed(self):
        return self.player.arrived

    def vars_for_template(self):
        # Retrieve the judge associated with the current player
        all_cases = Case.filter(subsession=self.subsession)

        current_judge_list = Judge.filter(subsession=self.subsession, player=self.player)
        current_judge = current_judge_list[0] if current_judge_list else None

        # If no judge is found, set to None (or handle as appropriate)
        if not current_judge:
            return {
                'selected_cases': [],
                'round_number': self.subsession.round_number,
                'arrived': self.player.arrived
            }

        # Fetch cases assigned to this specific judge using the relationship comparison
        selected_cases = Case.filter(subsession=self.subsession, judge=current_judge)

        # Convert the cases to a list of dictionaries for compatibility with HTML templates
        case_list = [
            {'id': case.id, 'case_id': case.case_id, 'points': case.points, 'judge_id': case.judge.judge_id}
            for case in selected_cases
        ]

        return {
            'all cases': all_cases,
            'judge': current_judge,
            'selected_cases': case_list,  # Pass the formatted list of selected cases
            'round_number': self.subsession.round_number,
            'arrived': self.player.arrived
        }

# Define the sequence of pages for the app
page_sequence = [
    ArrivalPage,
    SelectCasesPage,
    ResultsPage
]