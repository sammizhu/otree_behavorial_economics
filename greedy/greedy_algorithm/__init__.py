from otree.api import *

import random
import json

class Constants(BaseConstants):
    name_in_url = 'greedy_algorithm'
    players_per_group = None
    num_rounds = 1

class Subsession(BaseSubsession):
    print("Subsession class loaded")  # Debug statement

    def creating_session(self):
        print("Running creating_session...")  # Debug statement
        # Create 5 cases at the start of the session if they don't exist yet
        if not self.session.vars.get('cases'):
            cases = [
                Case.create(
                    session_id=self.session.id,
                    case_id=i + 1,
                    points=random.randint(1, 10),
                    is_assigned=False
                ) for i in range(5)
            ]
            self.session.vars['cases'] = [case.id for case in cases]

        # Create a judge for each player if not already created
        if not self.session.vars.get('judges'):
            judges = [
                Judge.create(
                    session_id=self.session.id,
                    player_id=player.id,
                    judge_id=player.id_in_group
                ) for player in self.get_players()
            ]
            self.session.vars['judges'] = [judge.id for judge in judges]

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    arrived = models.BooleanField(initial=False)
    selected_case_ids = models.LongStringField(blank=True, default='[]')

    @property
    def selected_cases_list(player):
        return json.loads(player.selected_case_ids)

    @selected_cases_list.setter
    def selected_cases_list(player, value):
        player.selected_case_ids = json.dumps(value)

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
        # Fetch cases that belong to the current session using the 'session_id'
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
            judge = Judge.objects_filter(session_id=player.session.id, player_id=player.id)[0]
            case.judge_id = judge.id
            case.is_assigned = True
            player.selected_cases_list.append(case_id)

            return {0: {'action': 'case_selected', 'case_id': case_id}}

        return {player.id_in_group: {'action': 'case_unavailable', 'case_id': case_id}}

def vars_for_template(player):
    session = player.session
    judge = next((Judge.objects_get(id=judge_id) for judge_id in session.vars.get('judges', []) if Judge.objects_get(id=judge_id).player_id == player.id), None)
    selected_cases = [Case.objects_get(id=case_id) for case_id in session.vars.get('cases', []) if Case.objects_get(id=case_id).judge_id == judge.id] if judge else []
    return dict(selected_cases=selected_cases, round_number=player.subsession.round_number)

def is_displayed(player):
    player.arrived = True
    return True

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
        return vars_for_template(player)

class GameSummaryPage(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == Constants.num_rounds

    @staticmethod
    def vars_for_template(player):
        session = player.session
        judges = [Judge.objects_get(id=judge_id) for judge_id in session.vars.get('judges', [])]
        judge_stats = []

        for judge in judges:
            assigned_cases = [Case.objects_get(id=case_id) for case_id in session.vars.get('cases', []) if Case.objects_get(id=case_id).judge_id == judge.id]
            total_points = sum(case.points for case in assigned_cases)

            judge_stats.append({
                'judge_id': judge.judge_id,
                'player_id': judge.player_id,
                'assigned_cases': [{'case_id': case.case_id, 'points': case.points} for case in assigned_cases],
                'total_points': total_points
            })

        return dict(judge_stats=judge_stats)

page_sequence = [ArrivalPage, SelectCasesPage, ResultsPage, GameSummaryPage]