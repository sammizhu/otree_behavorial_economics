from otree.api import *
import random
import json

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
    # Dynamically create bid fields for up to 10 cases
    assigned_case_ids = models.StringField(blank=True, doc="Stores assigned case IDs as a JSON string")
    player_payoff = models.CurrencyField(initial=0, doc="Player's total payoff")


# Add bid fields dynamically
for i in range(1, 11):  # Adjust the range to match the maximum number of cases
    setattr(
        Player,
        f"bid_case_{i}",
        models.CurrencyField(
            min=C.BID_MIN,
            max=C.BID_MAX,
            label=f"Bid for Case {i}",
        ),
    )


class Case(ExtraModel):
    subsession = models.Link(Subsession)
    case_id = models.IntegerField()
    is_assigned = models.BooleanField(default=False)
    assigned_player = models.Link(Player)


class CaseBid(ExtraModel):
    subsession = models.Link(Subsession)
    player = models.Link(Player)
    case = models.Link(Case)
    bid_amount = models.CurrencyField(min=C.BID_MIN, max=C.BID_MAX)


# FUNCTIONS
def creating_session(subsession: Subsession):
    num_cases = subsession.session.config.get('num_cases', 5)
    subsession.session.vars['num_cases'] = num_cases

    for i in range(1, num_cases + 1):
        Case.create(subsession=subsession, case_id=i)


def set_assignments(group: Group):
    subsession = group.subsession
    cases = Case.filter(subsession=subsession)
    for case in cases:
        case_bids = CaseBid.filter(subsession=subsession, case=case)
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
            winner_player.player_payoff += C.BID_MAX - winner_bid.bid_amount

class Bid(Page):
    form_model = 'player'

    @staticmethod
    def get_form_fields(player):
        # Dynamically generate form fields for all cases
        num_cases = player.subsession.session.vars['num_cases']
        return [f"bid_case_{i}" for i in range(1, num_cases + 1)]

    @staticmethod
    def vars_for_template(player):
        # Pass case details for rendering in the template
        num_cases = player.subsession.session.vars['num_cases']
        cases = [
            {
                'case_id': i,
                'description': f"Details for Case {i}",
                'form_field_name': f"bid_case_{i}",
            }
            for i in range(1, num_cases + 1)
        ]
        return {
            'cases': cases,
            'bid_min': C.BID_MIN,
            'bid_max': C.BID_MAX,
            'player_id_in_group': player.id_in_group,
        }

    @staticmethod
    def before_next_page(player, timeout_happened):
        num_cases = player.subsession.session.vars['num_cases']
        for i in range(1, num_cases + 1):
            bid_amount = getattr(player, f"bid_case_{i}")
            cases = Case.filter(subsession=player.subsession, case_id=i)
            case = cases[0] if cases else None
            if case:
                CaseBid.create(
                    subsession=player.subsession,
                    case=case,
                    player=player,
                    bid_amount=bid_amount,
                )

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = set_assignments


class Results(Page):
    @staticmethod
    def vars_for_template(player):
        assigned_case_ids_str = player.field_maybe_none('assigned_case_ids') or "[]"
        assigned_cases = json.loads(assigned_case_ids_str)
        return {
            'assigned_cases': assigned_cases,
            'player_bids': CaseBid.filter(subsession=player.subsession, player=player),
            'player_id_in_group': player.id_in_group,
        }


page_sequence = [Bid, ResultsWaitPage, Results]