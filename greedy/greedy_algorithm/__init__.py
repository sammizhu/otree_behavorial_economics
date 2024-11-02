from otree.api import *
import json
import random

from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer, ExtraModel
)
import random
import json
from otree.models import Session  # Import Session model to link judges and cases with a session.

class Constants(BaseConstants):
    """
    Defines global constants for the app, such as URL, number of rounds, and group size.
    """
    name_in_url = 'greedy_algorithm'
    players_per_group = None  # No predefined group size.
    num_rounds = 5  # Simulate 5 time periods (rounds).

class Subsession(BaseSubsession):
    """
    Handles the session setup and data creation logic for each round.
    """
    pass

def creating_session(subsession: Subsession):
        """
        Initializes cases and judges at the beginning of the session. 
        Cases are created only in the first round, while unassigned cases carry over in subsequent rounds.
        Judges are created for each player at every round.
        """
        cases = []

        # Create cases only in the first round
        if subsession.round_number == 1:
            for i in range(5):
                case = Case.create(
                    session=subsession.session,  # Corrected: use session, not subsession
                    case_id=i + 1,
                    points=random.randint(1, 10),
                    is_assigned=False
                )
                cases.append(case)

            # Save case IDs in session vars
            subsession.session.vars['cases'] = [case.id for case in cases]
        else:
            # Carry over unassigned cases from previous rounds
            cases = Case.filter(session=subsession.session)
            subsession.session.vars['cases'] = [
                case.id for case in cases if not case.is_assigned
            ]

        # Create a new judge for each player for the current round
        judges = []
        for player in subsession.get_players():
            judge = Judge.create(
                session=subsession.session,  # Corrected: use session, not subsession
                player=player,
                judge_id=player.id + (subsession.round_number - 1) * 100
            )
            judges.append(judge)

        # Store judge IDs in session vars
        subsession.session.vars[f'judges_round_{subsession.round_number}'] = [judge.id for judge in judges]

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

class Group(BaseGroup):
    """
    A placeholder for group-level data, which is not used in this setup.
    """
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

class Judge(ExtraModel):
    """
    Stores information about judges, linking them to players and sessions.
    """
    session = models.Link(Session)  # Links the judge to a session.
    player = models.Link(Player)  # Associates the judge with a specific player.
    judge_id = models.IntegerField()  # Unique ID for the judge.

class Case(ExtraModel):
    """
    Represents a case in the experiment, tracking assignment status and points.
    """
    session = models.Link(Session)  # Links the case to a session.
    case_id = models.IntegerField()  # Unique ID for the case.
    points = models.IntegerField()  # Points associated with the case.
    is_assigned = models.BooleanField(default=False)  # Tracks whether the case is assigned.
    judge = models.Link(Judge)  # Links the case to the judge that selects it.

class ArrivalPage(Page):
    """
    Handles the arrival of players (judges) at the start of the round.
    """
    @staticmethod
    def is_displayed(player: Player):
        """
        Simulates the arrival of a judge. Always displayed to update arrival status.
        """
        player.arrived = True
        return True  # Always display to update arrival status

    @staticmethod
    def vars_for_template(player: Player):
        """
        Provides variables for the HTML template, including available unassigned cases.
        """
        # Fetch unassigned cases for the current session
        cases = Case.filter(session=player.session, is_assigned=False)

        return {
            'cases': cases,
            'arrived': player.arrived,
            'round_number': player.subsession.round_number
        }

class SelectCasesPage(Page):
    live_method = live_method

    @staticmethod
    def is_displayed(player):
        # Display only if not all players have completed the task
        return player.arrived

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
    """
    Displays the results of the current round, including selected cases for each judge.
    """

    @staticmethod
    def is_displayed(player: Player):
        """
        Only display if the judge has arrived.
        """
        return player.arrived

    @staticmethod
    def vars_for_template(player: Player):
        """
        Provides the selected cases and judge information for the template.
        """
        # Retrieve the judge associated with the current player
        all_cases = Case.filter(session=player.session)

        current_judges = Judge.filter(session=player.session, player=player)
        if current_judges:
            current_judge = current_judges[0]
        else:
            current_judge = None

        if not current_judge:
            return {
                'selected_cases': [],
                'round_number': player.subsession.round_number,
                'arrived': player.arrived
            }

        # Fetch cases assigned to this specific judge
        selected_cases = Case.filter(session=player.session, judge=current_judge)

        # Convert the cases to a list of dictionaries for compatibility with HTML templates
        case_list = [
            {'id': case.id, 'case_id': case.case_id, 'points': case.points, 'judge_id': case.judge.judge_id}
            for case in selected_cases
        ]

        return {
            'all_cases': all_cases,
            'judge': current_judge,
            'selected_cases': case_list,
            'round_number': player.subsession.round_number,
            'arrived': player.arrived
        }

class GameSummaryPage(Page):
    """
    Displays the summary of the game after the last round, including judge statistics.
    """
    @staticmethod
    def is_displayed(player: Player):
        """
        Only display this page after the final round.
        """
        return player.round_number == Constants.num_rounds

    @staticmethod
    def vars_for_template(player: Player):
        """
        Provides a summary of all judges and their assigned cases for the template.
        """
        # Fetch all judges from the session
        judges = Judge.filter(session=player.session)

        # Collect stats for each judge
        judge_stats = []
        for judge in judges:
            assigned_cases = Case.filter(session=player.session, judge=judge)

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

        return {'judge_stats': judge_stats}

# Define the sequence of pages for the app
page_sequence = [
    ArrivalPage,
    SelectCasesPage,
    ResultsPage,
    GameSummaryPage
]