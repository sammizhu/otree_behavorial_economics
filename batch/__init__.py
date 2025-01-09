from otree.api import *
import random
import json
import io
import csv

doc = """
In this game, players bid on cases. The player with the lowest bid wins the case.
"""

class C(BaseConstants):
    NAME_IN_URL = 'case_assignment_auction'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    BID_MIN = cu(0)
    BID_MAX = cu(10)


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    username = models.StringField(blank=True)
    password = models.StringField(blank=True)

    # This will store the entire CSV text that the admin pastes in.
    csv_data = models.LongStringField(blank=True)

    # For Judges
    assigned_case_ids = models.StringField(blank=True, doc="Stores assigned case IDs as a JSON string")
    player_payoff = models.CurrencyField(initial=0, doc="Player's total payoff")



# Add bid fields dynamically
for i in range(1, 100):  #statically set 100 as the maximum number of cases
    setattr(
        Player,
        f"bid_case_{i}",
        models.CurrencyField(
            blank=True,
            min=C.BID_MIN,
            max=C.BID_MAX,
            label=f"Bid for Case {i}",
        ),
    )


class Case(ExtraModel):
    subsession = models.Link(Subsession)
    case_id = models.IntegerField()
    case_type = models.StringField()
    region = models.StringField()
    priority = models.StringField()
    points = models.IntegerField()
    date_filled = models.StringField()
    description = models.LongStringField()
    # assignment logic
    is_assigned = models.BooleanField(default=False)
    assigned_player = models.Link(Player)


class CaseBid(ExtraModel):
    subsession = models.Link(Subsession)
    player = models.Link(Player)
    case = models.Link(Case)
    bid_amount = models.CurrencyField(min=C.BID_MIN, max=C.BID_MAX)


# FUNCTIONS
def creating_session(subsession: Subsession):
    pass

def set_assignments(group: Group):
    subsession = group.subsession
    cases = Case.filter(subsession=subsession)
    for case in cases:
        case_bids = CaseBid.filter(subsession=subsession, case=case)
        case_bids = [bid for bid in case_bids if bid.bid_amount is not None]
        if case_bids:
            min_bid_amount = min(bid.bid_amount for bid in case_bids)
            lowest_bidders = [bid for bid in case_bids if bid.bid_amount == min_bid_amount]
            winner_bid = random.choice(lowest_bidders)
            winner_player = winner_bid.player
            case.is_assigned = True
            case.assigned_player = winner_player

            assigned_case_ids_str = winner_player.field_maybe_none('assigned_case_ids') or "[]"
            assigned_cases = json.loads(assigned_case_ids_str)
            assigned_cases.append(case.case_id)
            winner_player.assigned_case_ids = json.dumps(assigned_cases)
            winner_player.player_payoff += winner_bid.bid_amount

class Login(Page):
    form_model = 'player'
    form_fields = ['username', 'password']

    @staticmethod
    def vars_for_template(player: Player):
        return {}

    @staticmethod
    def error_message(player: Player, values):
        # You can do more complex checks here
        if not (values['username'] and values['password']):
            return "Please enter both username and password."

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        # Example: if user enters admin / admin, we treat them as admin
        # else if user enters judge / judge, we treat them as judge.
        # In reality, you might have a dictionary of valid credentials.

        username = player.username
        password = player.password
        print(username, password)
        
        if username == "admin" and password == "admin":
            player.participant.vars['role'] = "admin"
        elif username.startswith("judge") and password == "judge":
            player.participant.vars['role'] = "judge"
        else:
            print("Incorrect username and password combination. Please try again.")
            return ValueError

class Admin(Page):
    form_model = 'player'
    form_fields = ['csv_data']

    @staticmethod
    def before_next_page(player: Player, timeout_happened):

        # Parse CSV from the text field
        data_str = player.csv_data or ""
        if not data_str.strip():
            return  # No data uploaded
        
        f = io.StringIO(data_str)
        reader = csv.DictReader(f, delimiter=',') 

        num_cases = 0

        # For each row, create a new Case
        for row in reader:
            num_cases += 1
            # adapt the keys to match your CSV headers exactly
            Case.create(
                subsession=player.subsession,
                case_id=int(row['Case_ID']),
                case_type=row['Case_Type'],
                region=row['Region'],
                priority=row['Priority'],
                points=int(row['Points']),
                date_filled=row['Date_Filled'],
                description=row['Description'],
            )

        player.subsession.session.vars['num_cases'] = num_cases

    @staticmethod
    def is_displayed(player: Player):
        # Show only if this player is 'admin', for example
        return player.participant.vars.get('role') == 'admin'

class AdminReview(Page):
    """
    Page shown after AdminHome, to display the newly created cases.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get('role') == 'admin'

    @staticmethod
    def vars_for_template(player: Player):
        return {
            'cases': Case.filter(subsession=player.subsession),
            'num_cases': player.subsession.session.vars['num_cases']
        }

class Bid(Page):
    form_model = 'player'

    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get('role') == 'judge'

    @staticmethod
    def get_form_fields(player: Player):
        cases = Case.filter(subsession=player.subsession)
        cases_sorted = sorted(cases, key=lambda c: c.case_id)

        form_fields = []
        for c in cases_sorted:
            form_fields.append(f"bid_case_{c.case_id}")
        return form_fields

    @staticmethod
    def vars_for_template(player: Player):
        cases = Case.filter(subsession=player.subsession)
        cases_sorted = sorted(cases, key=lambda c: c.case_id)

        # Build a list of dicts for rendering in the template
        data_for_template = []
        for c in cases_sorted:
            data_for_template.append({
                'case_id': c.case_id,
                'case_type': c.case_type,
                'region': c.region,
                'priority': c.priority,
                'points': c.points,
                'date_filled': c.date_filled,
                'description': c.description,
                'form_field_name': f"bid_case_{c.case_id}",  
            })

        return {
            'cases': data_for_template,
            'bid_min': C.BID_MIN,
            'bid_max': C.BID_MAX,
            'player_id_in_group': player.id_in_group,
        }

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        cases = Case.filter(subsession=player.subsession)
        for c in cases:
            field_name = f"bid_case_{c.case_id}"
            bid_amount = player.field_maybe_none(field_name)
            if bid_amount is not None:
                CaseBid.create(
                    subsession=player.subsession,
                    case=c,
                    player=player,
                    bid_amount=bid_amount,
                )


class ResultsWaitPage(WaitPage):
    after_all_players_arrive = set_assignments

    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get('role') == 'judge'


class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get('role') == 'judge'

    @staticmethod
    def vars_for_template(player: Player):
        assigned_case_ids_str = player.field_maybe_none('assigned_case_ids') or "[]"
        assigned_cases = json.loads(assigned_case_ids_str)
        return {
            'assigned_cases': assigned_cases,
            'player_bids': CaseBid.filter(subsession=player.subsession, player=player),
            'player_id_in_group': player.id_in_group,
            'bid_max': C.BID_MAX
        }

page_sequence = [
    Login,      
    Admin,  
    AdminReview,
    Bid,        
    ResultsWaitPage,
    Results,
]