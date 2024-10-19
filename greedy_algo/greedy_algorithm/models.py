from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer, ExtraModel
)
import random
import json
from otree.models import Session  # Import Session model

class Constants(BaseConstants):
    name_in_url = 'greedy_algorithm'
    players_per_group = None
    num_rounds = 10  # Simulate 10 time periods

class Subsession(BaseSubsession):
    def creating_session(self):
        if self.round_number == 1:
            cases = []
            judges = []

            # Create initial cases
            for i in range(5):
                case = Case.create(
                    session=self.session,  # Link case to the session
                    case_id=i + 1,
                    points=random.randint(1, 10),
                    is_assigned=False
                )
                cases.append(case)

            # Create judges for each player in the first round and link to the player
            for player in self.get_players():
                judge = Judge.create(
                    session=self.session,  # Link judge to the session
                    player=player,         # Link judge to the current player
                    judge_id=player.id
                )
                judges.append(judge)

            # Save case IDs in session.vars (optional)
            self.session.vars['cases'] = [case.id for case in cases]
            self.session.vars['judges'] = [judge.id for judge in judges]

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    arrived = models.BooleanField(initial=False)
    selected_case_ids = models.LongStringField(blank=True)

    @property
    def selected_cases_list(self):
        if self.selected_case_ids:
            return json.loads(self.selected_case_ids)
        return []

    @selected_cases_list.setter
    def selected_cases_list(self, value):
        self.selected_case_ids = json.dumps(value)

class Judge(ExtraModel):
    session = models.Link(Session)
    judge_id = models.IntegerField()
    player = models.Link(Player)

class Case(ExtraModel):
    session = models.Link(Session)  # Use Session class, not string
    judge = models.Link(Judge)      # Use Judge class, not string
    case_id = models.IntegerField()
    points = models.IntegerField(default=0)
    is_assigned = models.BooleanField(default=False)