from otree.api import *
import json
import random
from otree.models import Session

class Constants(BaseConstants):
    name_in_url = 'greedy_algorithm'
    players_per_group = None  # Each participant is in their own group
    num_rounds = 1  # This will be overridden dynamically in creating_session

class Subsession(BaseSubsession):
    pass

def creating_session(subsession: Subsession):
    """
    Initializes cases and judges at the beginning of the session.
    """
    # Set `num_rounds` based on settings.py value and store it in `session.vars`
    num_rounds = subsession.session.config.get('num_demo_participants', 1)
    subsession.session.vars['num_rounds'] = num_rounds
    
    if subsession.round_number == 1:
        # Initialize cases for the first round
        cases = []
        for i in range(5):
            case = Case.create(
                session=subsession.session,
                case_id=i + 1,
                points=random.randint(1, 10),
                is_assigned=False
            )
            cases.append(case)
        subsession.session.vars['cases'] = [case.id for case in cases]

    # Create a new judge for each player for the current round
    for player in subsession.get_players():
        Judge.create(
            session=subsession.session,
            player=player,
            judge_id=player.id + (subsession.round_number - 1) * 100
        )

def live_method(player, data):
    action = data.get('action')
    
    if action == 'load':
        # Filter only unassigned cases for load action
        cases = Case.objects_filter(session_id=player.session.id, is_assigned=False)
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
        # Handle case selection
        case_id = int(data.get('case_id'))
        case_list = Case.objects_filter(session_id=player.session.id, id=case_id, is_assigned=False)
        
        if not case_list:
            return {player.id_in_group: {'action': 'case_not_found', 'case_id': case_id}}
        
        case = case_list[0]
        judge = Judge.objects_filter(session_id=player.session.id, player_id=player.id).first()
        
        if judge:
            selected_cases = player.selected_cases_list
            if case_id not in selected_cases:
                selected_cases.append(case_id)
                player.selected_cases_list = selected_cases
            return {player.id_in_group: {'action': 'case_assigned', 'case_id': case_id}}
        
        return {player.id_in_group: {'action': 'case_unavailable', 'case_id': case_id}}
    
    elif action == 'unselect_case':
        # Handle case unselection
        case_id = int(data.get('case_id'))
        selected_cases = player.selected_cases_list
        
        if case_id in selected_cases:
            selected_cases.remove(case_id)
            player.selected_cases_list = selected_cases
        
        return {player.id_in_group: {'action': 'case_unselected', 'case_id': case_id}}

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    selected_case_ids = models.LongStringField(blank=True, default='[]')

    @property
    def selected_cases_list(self):
        return json.loads(self.selected_case_ids)

    @selected_cases_list.setter
    def selected_cases_list(self, value):
        self.selected_case_ids = json.dumps(value)
    

class Judge(ExtraModel):
    session = models.Link(Session)
    player = models.Link(Player)
    judge_id = models.IntegerField()

class Case(ExtraModel):
    session = models.Link(Session)
    case_id = models.IntegerField()
    points = models.IntegerField()
    is_assigned = models.BooleanField(default=False)
    judge = models.Link(Judge)

class ArrivalPage(Page):
    @staticmethod
    def is_displayed(player: Player):
        return True
    
    @staticmethod
    def vars_for_template(player: Player):
        # Filter only unassigned cases
        cases = Case.filter(session=player.session, is_assigned=False)
        return {
            'cases': cases,
            'round_number': player.subsession.round_number
        }

class SelectCasesPage(Page):
    live_method = live_method
    form_model = 'player'
    form_fields = ['selected_case_ids']

    @staticmethod
    def is_displayed(player: Player):
        # Display SelectCasesPage if rounds are not complete
        return player.round_number < player.session.vars['num_rounds']

    @staticmethod
    def vars_for_template(player):
        # Filter only unassigned cases
        cases = list(Case.objects_filter(session_id=player.session.id, is_assigned=False))
        for case in cases:
            case.points += 1
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
        player.session.vars['cases'] = [case.id for case in cases]
        return {
            'cases': [{'id': case.id, 'case_id': case.case_id, 'points': case.points} for case in cases],
            'round_number': player.subsession.round_number,
        }

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        """
        Sets the selected cases to 'assigned' after submission.
        """
        selected_case_ids = json.loads(player.selected_case_ids or '[]')
        current_judge = Judge.objects_filter(session_id=player.session.id, player_id=player.id).first()

        # First, reset any previously assigned cases for this judge
        previously_selected_cases = Case.objects_filter(session_id=player.session.id, judge=current_judge)
        for case in previously_selected_cases:
            case.is_assigned = False
            case.judge = None

        # Now, assign only the cases that are selected in the current submission
        for case_id in selected_case_ids:
            case = Case.objects_filter(session_id=player.session.id, id=case_id).first()
            if case and not case.is_assigned:
                case.is_assigned = True
                case.judge = current_judge

class ResultsPage(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number < player.session.vars['num_rounds']

    @staticmethod
    def vars_for_template(player: Player):
        all_cases = Case.filter(session=player.session)
        current_judge_list = Judge.filter(session=player.session, player=player)
        current_judge = current_judge_list[0] if current_judge_list else None
        if not current_judge:
            return {
                'selected_cases': [],
                'round_number': player.subsession.round_number,
                'arrived': player.arrived
            }
        selected_cases = Case.filter(session=player.session, judge=current_judge)
        
        # Calculate total points of selected cases
        total_points = sum(case.points for case in selected_cases)
        
        # Set the player's payoff
        player.payoff = total_points
        
        case_list = [
            {'id': case.id, 'case_id': case.case_id, 'points': case.points, 'judge_id': case.judge.judge_id}
            for case in selected_cases
        ]
        return {
            'all_cases': all_cases,
            'judge': current_judge,
            'selected_cases': case_list,
            'round_number': player.subsession.round_number,
            'total_points': total_points  # For display purposes
        }

page_sequence = [
    ArrivalPage,
    SelectCasesPage,
    ResultsPage,
]