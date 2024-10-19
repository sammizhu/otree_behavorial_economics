from otree.api import Page
from .models import Constants, Case, Judge
import json
import random

class ArrivalPage(Page):
    """
    Handles the arrival of players (judges) at the start of the round.
    """

    def is_displayed(self):
        """
        Simulates the arrival of a judge. Always displayed to update arrival status.
        """
        self.player.arrived = True
        return True

    def vars_for_template(self):
        """
        Provides variables for the HTML template, including available unassigned cases.
        """
        cases = Case.filter(session=self.session, is_assigned=False)
        return {
            'cases': cases,
            'arrived': self.player.arrived,
            'round_number': self.subsession.round_number
        }

class SelectCasesPage(Page):
    """
    Allows players (judges) to select cases for the current round.
    """
    form_model = 'player'
    form_fields = ['selected_case_ids']

    def is_displayed(self):
        """
        Only display this page if the judge has arrived.
        """
        return self.player.arrived

    def vars_for_template(self):
        """
        Provides variables for the template, including available cases.
        Ensures there are at least 5 cases available each round.
        """
        case_ids = self.session.vars.get('cases', [])
        cases = []

        # Update points for unassigned cases
        for case_id in case_ids:
            matching_cases = Case.filter(session=self.session, id=case_id)
            if matching_cases:
                case = matching_cases[0]
                if not case.is_assigned:
                    case.points += 1
                cases.append(case)

        # Find the highest existing case ID
        all_cases = Case.filter(session=self.session)
        max_case_id = max((case.case_id for case in all_cases), default=0)

        # Ensure a minimum of 5 unassigned cases
        needed_cases = 5 - len([case for case in cases if not case.is_assigned])
        new_cases = [
            Case.create(
                session=self.session,
                case_id=max_case_id + i + 1,
                points=random.randint(1, 10),
                is_assigned=False
            )
            for i in range(needed_cases)
        ]

        cases.extend(new_cases)
        self.session.vars['cases'] = [case.id for case in cases]

        # Prepare case data for template rendering
        case_list = [{'id': case.id, 'case_id': case.case_id, 'points': case.points} for case in cases]
        return {
            'cases': case_list,
            'round_number': self.subsession.round_number,
            'arrived': self.player.arrived,
        }

    def before_next_page(self):
        """
        Processes selected case IDs and assigns them to the current judge.
        """
        raw_data = self._form_data.getlist('selected_case_ids[]')
        self.player.selected_case_ids = json.dumps(raw_data)

        if raw_data:
            self.player.selected_cases_list = [int(cid) for cid in raw_data]

            # Fetch the current judge for this player
            current_judge = Judge.filter(session=self.session, player=self.player).first()

            # Assign selected cases to the judge
            for case_id in self.player.selected_cases_list:
                case = Case.filter(session=self.session, id=case_id).first()
                case.is_assigned = True
                case.judge = current_judge

            # Remove assigned cases from session variables
            self.session.vars['cases'] = [
                cid for cid in self.session.vars['cases'] 
                if cid not in self.player.selected_cases_list
            ]
        else:
            self.player.selected_cases_list = []

class ResultsPage(Page):
    """
    Displays the results of the current round, including selected cases for each judge.
    """

    def is_displayed(self):
        """
        Only display if the judge has arrived.
        """
        return self.player.arrived

    def vars_for_template(self):
        """
        Provides the selected cases and judge information for the template.
        """
        all_cases = Case.filter(session=self.session)
        current_judge = Judge.filter(session=self.session, player=self.player).first()

        if not current_judge:
            return {
                'selected_cases': [],
                'round_number': self.subsession.round_number,
                'arrived': self.player.arrived
            }

        selected_cases = Case.filter(session=self.session, judge=current_judge)
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
    """
    Displays the summary of the game after the last round, including judge statistics.
    """

    def is_displayed(self):
        """
        Only display this page after the final round.
        """
        return self.round_number == Constants.num_rounds

    def vars_for_template(self):
        """
        Provides a summary of all judges and their assigned cases for the template.
        """
        judges = Judge.filter(session=self.session)
        judge_stats = []

        # Collect statistics for each judge
        for judge in judges:
            assigned_cases = Case.filter(session=self.session, judge=judge)
            case_data = [{'case_id': case.case_id, 'points': case.points} for case in assigned_cases]
            total_points = sum(case.points for case in assigned_cases)

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