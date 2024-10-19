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
        # Fetch case IDs from session vars
        case_ids = self.session.vars.get('cases', [])

        # Retrieve all case objects and increment points for unassigned ones
        cases = []
        for case_id in case_ids:
            matching_cases = Case.filter(session=self.session, id=case_id)
            if matching_cases:
                case = matching_cases[0]
                if not case.is_assigned:
                    case.points += 1  # Increment points for unassigned cases
                cases.append(case)

        # Retrieve the highest existing case ID across all cases
        all_cases = Case.filter(session=self.session)
        if all_cases:
            max_case_id = max(case.case_id for case in all_cases)
        else:
            max_case_id = 0

        # Ensure there are 5 available cases
        needed_cases = 5 - len([case for case in cases if not case.is_assigned])

        new_cases = [
            Case.create(
                session=self.session,
                case_id=max_case_id + i + 1,  # Ensure case IDs are sequential
                points=random.randint(1, 10),
                is_assigned=False
            )
            for i in range(needed_cases)
        ]

        # Add new cases to the list and update session vars
        cases.extend(new_cases)
        self.session.vars['cases'] = [case.id for case in cases]

        # Convert cases to dictionaries for template rendering
        case_list = [{'id': case.id, 'case_id': case.case_id, 'points': case.points} for case in cases]

        return {
            'cases': case_list,
            'round_number': self.subsession.round_number,
            'arrived': self.player.arrived,
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

class GameSummaryPage(Page):
    def is_displayed(self):
        # Display this page only after the last round
        return self.round_number == Constants.num_rounds

    def vars_for_template(self):
        # Fetch all judges from the session
        judges = Judge.filter(session=self.session)

        # Collect stats for each judge
        judge_stats = []
        for judge in judges:
            assigned_cases = Case.filter(session=self.session, judge=judge)

            # Collect case information
            case_data = [
                {'case_id': case.case_id, 'points': case.points}
                for case in assigned_cases
            ]

            # Calculate total points assigned to this judge
            total_points = sum(case.points for case in assigned_cases)  # Use dot notation

            judge_stats.append({
                'judge_id': judge.judge_id,
                'player_id': judge.player.id,
                'assigned_cases': case_data,
                'total_points': total_points
            })

        # Debug: Print summary stats
        print(f"Game Summary Stats: {judge_stats}")

        return {'judge_stats': judge_stats}

# Define the sequence of pages for the app
page_sequence = [
    ArrivalPage,
    SelectCasesPage,
    ResultsPage,
    GameSummaryPage
]