from otree.api import Page
from .models import Case, Judge, Player, Constants

class ArrivalPage(Page):
    """
    Handles the arrival of players (judges).
    """

    def is_displayed(self):
        self.player.arrived = True
        return True

    def vars_for_template(self):
        return {
            'arrived': self.player.arrived,
            'round_number': self.subsession.round_number  # Provide the current round number.
        }

class SelectCasesPage(Page):
    """
    Handles the selection of cases by players using real-time updates.
    """

    @staticmethod
    def live_method(player, data):
        action = data.get('action')

        if action == 'load':
            cases = Case.filter(session=player.session)
            case_list = [
                {
                    'id': case.id,
                    'case_id': case.case_id,
                    'points': case.points,
                    'is_assigned': case.is_assigned
                }
                for case in cases
            ]
            selected_cases = player.selected_cases_list

            return {
                player.id_in_group: {
                    'action': 'load',
                    'cases': case_list,
                    'selected_cases': selected_cases
                }
            }

        elif action == 'select_case':
            case_id = int(data.get('case_id'))
            case_list = Case.filter(session=player.session, id=case_id)

            if not case_list:
                return {player.id_in_group: {'action': 'case_not_found', 'case_id': case_id}}

            case = case_list[0]
            if not case.is_assigned:
                judge = Judge.filter(session=player.session, player=player)[0]
                case.judge = judge
                case.is_assigned = True
                player.selected_cases_list.append(case_id)

                return {0: {'action': 'case_selected', 'case_id': case_id}}

            return {player.id_in_group: {'action': 'case_unavailable', 'case_id': case_id}}

class ResultsPage(Page):
    """
    Displays the selected cases for each judge.
    """

    def vars_for_template(self):
        judge = Judge.filter(session=self.session, player=self.player)[0]
        selected_cases = Case.filter(session=self.session, judge=judge)

        return {
            'selected_cases': selected_cases,
            'round_number': self.subsession.round_number
        }

class GameSummaryPage(Page):
    """
    Displays the overall summary at the end of the game.
    """

    def is_displayed(self):
        # Only display on the last round
        return self.round_number == Constants.num_rounds

    def vars_for_template(self):
        judges = Judge.filter(session=self.session)
        judge_stats = []

        for judge in judges:
            assigned_cases = Case.filter(session=self.session, judge=judge)
            total_points = sum(case.points for case in assigned_cases)

            judge_stats.append({
                'judge_id': judge.judge_id,
                'player_id': judge.player.id_in_group,
                'assigned_cases': [
                    {'case_id': case.case_id, 'points': case.points} for case in assigned_cases
                ],
                'total_points': total_points
            })

        return {'judge_stats': judge_stats}

page_sequence = [
    ArrivalPage,
    SelectCasesPage,
    ResultsPage,
    GameSummaryPage
]