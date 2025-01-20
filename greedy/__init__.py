from otree.api import *
import random
import json
import io
import csv

doc = """
In this game, players start with 2000 points. They select cases. 
They cannot exceed their budget.
"""

class C(BaseConstants):
    NAME_IN_URL = 'greedyalgo'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    BID_MIN = cu(0)
    BID_MAX = cu(10)

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    # The player's total budget of points
    budget = models.IntegerField(initial=2000)

    # Holds which case IDs (from the CSV) the player selected
    selected_case_ids = models.LongStringField(blank=True, default='[]')

    @property
    def selected_cases_list(self):
        return json.loads(self.selected_case_ids)

    @selected_cases_list.setter
    def selected_cases_list(self, value):
        self.selected_case_ids = json.dumps(value)

    username = models.StringField(blank=True)
    password = models.StringField(blank=True)

    # For Admin: Store entire CSV text
    csv_data = models.LongStringField(blank=True)


# If you still want the dynamic bidding fields (not strictly needed for a “greedy” approach)
for i in range(1, 100):
    setattr(
        Player,
        f"bid_case_{i}",
        models.CurrencyField(
            blank=True,
            min=cu(0),
            max=cu(10),
            label=f"Bid for Case {i}",
        ),
    )

class Judge(ExtraModel):
    subsession = models.Link(Subsession)
    player = models.Link(Player)
    judge_id = models.IntegerField()

class Case(ExtraModel):
    subsession = models.Link(Subsession)
    # The "case_id" here refers to the CSV column "Case_ID"
    case_id = models.IntegerField()
    case_type = models.StringField()
    region = models.StringField()
    priority = models.StringField()
    points = models.IntegerField()
    date_filled = models.StringField()
    description = models.LongStringField()

    # assignment logic
    is_assigned = models.BooleanField(default=False)
    assigned_judge = models.Link(Judge)


class CaseBid(ExtraModel):
    subsession = models.Link(Subsession)
    player = models.Link(Player)
    case = models.Link(Case)
    bid_amount = models.CurrencyField(min=cu(0), max=cu(10))


def creating_session(subsession: Subsession):
    """If you rely on role being set pre-session, you can create Judges here. 
    But typically we do it after login in `Login.before_next_page`."""
    for player in subsession.get_players():
        if player.participant.vars.get('role') == 'judge':
            Judge.create(
                subsession=subsession,
                player=player,
                judge_id=player.id_in_group  
            )


def live_method(player, data):
    """
    Logistic for Javascript on SelectCase.html that processes various
    actions of what users can do on the page (i.e. selecting a case, 
    unselecting a case, loading the case informaiton, etc).
    """
    action = data.get('action')
    
    if action == 'load':
        # Return all unassigned Cases
        cases = Case.filter(subsession=player.subsession, is_assigned=False)
        case_list = []
        for c in cases:
            case_list.append({
                'case_id': c.case_id,
                'case_type': c.case_type,
                'region': c.region,
                'priority': c.priority,
                'points': c.points,
                'date_filled': c.date_filled,
                'description': c.description,
                'is_assigned': c.is_assigned
            })
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
        case_list = Case.filter(subsession=player.subsession, case_id=case_id)
        if not case_list:
            return {player.id_in_group: {'action': 'case_not_found', 'case_id': case_id}}

        case = case_list[0]
        j_list = Judge.filter(subsession=player.subsession, player=player)
        judge = j_list[0] if j_list else None
        
        if not judge:
            return {player.id_in_group: {'action': 'case_unavailable', 'case_id': case_id}}

        # 1) Sum up existing selected cases
        selected_cases = player.selected_cases_list
        total_points_already = 0
        for cid in selected_cases:
            c_list2 = Case.filter(subsession=player.subsession, case_id=cid)
            if c_list2:
                total_points_already += c_list2[0].points

        # 2) Check if adding this new case's .points exceeds player's budget
        new_total = total_points_already + case.points
        if new_total > player.budget:
            # EXCEEDS BUDGET
            return {
                player.id_in_group: {
                    'action': 'exceed_budget',
                    'case_id': case_id,
                    'excess_amount': new_total - player.budget
                }
            }
        
        # If it does not exceed budget, we can add it
        if case_id not in selected_cases:
            selected_cases.append(case_id)
            player.selected_cases_list = selected_cases

        return {player.id_in_group: {'action': 'case_assigned', 'case_id': case_id}}

    elif action == 'unselect_case':
        case_id = int(data.get('case_id'))
        selected_cases = player.selected_cases_list
        if case_id in selected_cases:
            selected_cases.remove(case_id)
            player.selected_cases_list = selected_cases
        return {player.id_in_group: {'action': 'case_unselected', 'case_id': case_id}}


class Login(Page):
    """
    Given a set of username and password, directs the user to the head of 
    a sequence of pages.
    """
    form_model = 'player'
    form_fields = ['username', 'password']

    @staticmethod
    def error_message(player: Player, values):
        if not (values['username'] and values['password']):
            return "Please enter both username and password."

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        username = player.username
        password = player.password

        if username == "admin" and password == "admin": # change here to actual usernames and passwords
            player.participant.vars['role'] = "admin"
        elif username.startswith("judge") and password == "judge":
            player.participant.vars['role'] = "judge"
            # Create the Judge record right away
            Judge.create(
                subsession=player.subsession,
                player=player,
                judge_id=player.id_in_group
            )
        else:
            return ValueError


class Admin(Page):
    """
    Page for Admins to upload a CSV of court case information that 
    will be saved with a preview feature on the AdminReview page for
    Judges to select/bid for. 
    """
    form_model = 'player'
    form_fields = ['csv_data']

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        data_str = player.csv_data or ""
        if not data_str.strip():
            return
        f = io.StringIO(data_str)
        reader = csv.DictReader(f, delimiter=',') 
        num_cases = 0
        for row in reader:
            num_cases += 1
            Case.create(
                subsession=player.subsession,
                case_id=int(row['Case_ID']),
                case_type=row.get('Case_Type', ''),
                region=row.get('Region', ''),
                priority=row.get('Priority', ''),
                points=int(row.get('Points', 0)),
                date_filled=row.get('Date_Filled', ''),
                description=row.get('Description', ''),
            )

        player.subsession.session.vars['num_cases'] = num_cases

    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get('role') == 'admin'


class AdminReview(Page):
    """
    Fetches the cases uploaded in the CSV file for the Admin
    to review as a confirmation of upload.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get('role') == 'admin'

    @staticmethod
    def vars_for_template(player: Player):
        return {
            'cases': Case.filter(subsession=player.subsession),
            'num_cases': player.subsession.session.vars.get('num_cases', 0)
        }


class SelectCases(Page):
    """
    Greedy Algorithm 
    """
    live_method = live_method
    form_model = 'player'
    form_fields = ['selected_case_ids']

    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get('role') == 'judge'

    @staticmethod
    def vars_for_template(player: Player):
        cases = list(Case.filter(subsession=player.subsession, is_assigned=False))
        # you can mutate .points if you want to demonstrate something
        for c in cases:
            c.points += 1

        return {
            'cases': [
                {
                    'case_id': c.case_id,
                    'points': c.points
                }
                for c in cases
            ],
            'round_number': player.subsession.round_number,
            'budget': player.budget
        }

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        selected_case_ids = player.selected_cases_list
        j_list = Judge.filter(subsession=player.subsession, player=player)
        current_judge = j_list[0] if j_list else None

        if not current_judge:
            return

        # unassign old
        old_cases = Case.filter(subsession=player.subsession, assigned_judge=current_judge)
        for c in old_cases:
            c.is_assigned = False
            c.assigned_judge = None

        # assign new
        for cid in selected_case_ids:
            c_list = Case.filter(subsession=player.subsession, case_id=cid)
            if c_list:
                c = c_list[0]
                if not c.is_assigned:
                    c.is_assigned = True
                    c.assigned_judge = current_judge


class Results(Page):
    """
    Displays the outcome of each Judge after selecting cases.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get('role') == 'judge'

    @staticmethod
    def vars_for_template(player: Player):
        all_cases = Case.filter(subsession=player.subsession)
        j_list = Judge.filter(subsession=player.subsession, player=player)
        current_judge = j_list[0] if j_list else None

        if not current_judge:
            return {
                'selected_cases': [],
                'round_number': player.subsession.round_number,
            }
        selected_cases = Case.filter(subsession=player.subsession, assigned_judge=current_judge)
        spent_points = sum(c.points for c in selected_cases)
        leftover = player.budget - spent_points

        case_list = [
            {
                'case_id': c.case_id,
                'points': c.points,
                'judge_id': current_judge.judge_id
            }
            for c in selected_cases
        ]
        return {
            'all_cases': all_cases,
            'judge': current_judge,
            'selected_cases': case_list,
            'round_number': player.subsession.round_number,
            'spent_points': spent_points,
            'leftover': leftover
        }


page_sequence = [
    Login,
    Admin,
    AdminReview,
    SelectCases,
    Results
]