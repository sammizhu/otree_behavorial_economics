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
    # Create 5 cases at the start of the session if they don't exist yet
    if not subsession.session.vars.get('cases'):
        cases = [
            Case.create(
                session_id=subsession.session.id,
                case_id=i + 1,
                points=random.randint(1, 10),
                is_assigned=False
            ) for i in range(5)
        ]
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

        # Only include judges with assigned cases (total_points > 0)
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
        player.arrived = True  # Set player as arrived
        return True

    @staticmethod
    def vars_for_template(player):
        return {
            'arrived': player.arrived,
            'round_number': player.subsession.round_number,
        }

class SelectCasesPage(Page):
    live_method = live_method

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

page_sequence = [ArrivalPage, SelectCasesPage, ResultsPage, GameSummaryPage]