from otree.api import *
import random
import json

class Constants(BaseConstants):
    name_in_url = 'greedy_algorithm'
    players_per_group = None
    num_rounds = 1

class Subsession(BaseSubsession):
    pass

def creating_session(subsession: Subsession):
    """
    Initializes cases and judges at the beginning of the session.
    If fewer than 5 unassigned cases are available, new cases are introduced.
    Points of unassigned cases are incremented by 1.
    """
    # Retrieve all cases for the session and convert to list
    cases = list(Case.objects_filter(session_id=subsession.session.id))

    # Increment points for unassigned cases
    for case in cases:
        if not case.is_assigned:
            case.points += 1

    # Check the number of unassigned cases
    unassigned_cases = [case for case in cases if not case.is_assigned]
    unassigned_count = len(unassigned_cases)

    # Add new cases if fewer than 5 unassigned cases exist
    if unassigned_count < 5:
        for i in range(5 - unassigned_count):
            new_case = Case.create(
                session_id=subsession.session.id,
                case_id=len(cases) + i + 1,  # Ensure unique case IDs
                points=random.randint(1, 10),
                is_assigned=False
            )
            cases.append(new_case)

    # Update session vars with case IDs
    subsession.session.vars['cases'] = [case.id for case in cases]

    # Create a judge for each player if not already created
    if not subsession.session.vars.get('judges'):
        judges = [
            Judge.create(
                session_id=subsession.session.id,
                player_id=player.id,
                judge_id=player.id_in_group
            ) for player in subsession.get_players()
        ]
        subsession.session.vars['judges'] = [judge.id for judge in judges]

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    arrived = models.BooleanField(initial=False)
    selected_case_ids = models.LongStringField(blank=True, default='[]')
    task_completed = models.BooleanField(initial=False)  # Track if player has completed the task

    @property
    def selected_cases_list(self):
        return json.loads(self.selected_case_ids)

    @selected_cases_list.setter
    def selected_cases_list(self, value):
        self.selected_case_ids = json.dumps(value)

class Case(ExtraModel):
    session_id = models.IntegerField()
    case_id = models.IntegerField()
    points = models.IntegerField()
    is_assigned = models.BooleanField(default=False)
    judge_id = models.IntegerField(blank=True)

class Judge(ExtraModel):
    session_id = models.IntegerField()
    player_id = models.IntegerField()
    judge_id = models.IntegerField()

# FUNCTIONS
def live_method(player, data):
    action = data.get('action')

    if action == 'load':
        cases = Case.objects_filter(session_id=player.session.id)
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
        case_list = Case.objects_filter(session_id=player.session.id, id=case_id)

        if not case_list:
            return {player.id_in_group: {'action': 'case_not_found', 'case_id': case_id}}

        case = case_list[0]
        if not case.is_assigned:
            judge = Judge.objects_filter(session_id=player.session.id, player_id=player.id).first()
            if judge:
                case.judge_id = judge.id
                case.is_assigned = True

                selected_cases = player.selected_cases_list
                selected_cases.append(case_id)
                player.selected_cases_list = selected_cases

                return {0: {'action': 'case_selected', 'case_id': case_id}}

        return {player.id_in_group: {'action': 'case_unavailable', 'case_id': case_id}}

def results_vars_for_template(player):
    selected_cases = [
        Case.objects_filter(id=case_id).first()
        for case_id in player.selected_cases_list
    ]
    return dict(selected_cases=selected_cases, round_number=player.subsession.round_number)

def summary_vars_for_template(player):
    judges = Judge.objects_filter(session_id=player.session.id)
    judge_stats = []

    for judge in judges:
        assigned_cases = Case.objects_filter(session_id=player.session.id, judge_id=judge.id)
        total_points = sum(case.points for case in assigned_cases)

        if total_points > 0:
            judge_stats.append({
                'judge_id': judge.judge_id,
                'player_id': judge.player_id,
                'assigned_cases': [
                    {'case_id': case.case_id, 'points': case.points} for case in assigned_cases
                ],
                'total_points': total_points
            })

    return {'judge_stats': judge_stats}

# PAGES
class ArrivalPage(Page):
    @staticmethod
    def is_displayed(player):
        # Only display if the player hasn't completed their task yet
        return not player.task_completed

    @staticmethod
    def before_next_page(player, timeout_happened):
        # Mark the player as completed once they finish the arrival step
        player.arrived = True
        player.task_completed = True

    @staticmethod
    def vars_for_template(player):
        # Each player only sees their own arrival status
        return {
            'arrived': player.arrived,
            'round_number': player.subsession.round_number,
        }

class SelectCasesPage(Page):
    live_method = live_method

    @staticmethod
    def is_displayed(player):
        # Display only if not all players have completed the task
        return not all(p.task_completed for p in player.subsession.get_players())

    @staticmethod
    def vars_for_template(player):
        # Fetch all unassigned cases as a list
        cases = list(Case.objects_filter(session_id=player.session.id, is_assigned=False))

        # Update points for each unassigned case
        for case in cases:
            case.points += 1

        # Add new cases if fewer than 5 are available
        if len(cases) < 5:
            max_case_id = max([case.case_id for case in Case.objects_filter(session_id=player.session.id)], default=0)
            new_cases = [
                Case.create(
                    session_id=player.session.id,
                    case_id=max_case_id + i + 1,
                    points=random.randint(1, 10),
                    is_assigned=False
                ) for i in range(5 - len(cases))
            ]
            cases.extend(new_cases)

        # Update session variables with the case IDs
        player.session.vars['cases'] = [case.id for case in cases]

        return {
            'cases': [{'id': case.id, 'case_id': case.case_id, 'points': case.points} for case in cases],
            'round_number': player.subsession.round_number,
            'arrived': player.arrived,
        }

class ResultsPage(Page):
    @staticmethod
    def vars_for_template(player):
        return results_vars_for_template(player)

class GameSummaryPage(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == Constants.num_rounds

    @staticmethod
    def vars_for_template(player):
        return summary_vars_for_template(player)

# Loop pages until conditions are met
page_sequence = [ArrivalPage, SelectCasesPage, ResultsPage, GameSummaryPage]