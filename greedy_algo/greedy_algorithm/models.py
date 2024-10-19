from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer, ExtraModel
)
import random
import json
from otree.models import Session  # Import Session model

class Constants(BaseConstants):
    name_in_url = 'greedy_algorithm'
    players_per_group = None
    num_rounds = 2  # Simulate 10 time periods

class Subsession(BaseSubsession):
    def creating_session(self):
        cases = []

        # Create cases only in the first round
        if self.round_number == 1:
            for i in range(5):
                case = Case.create(
                    session=self.session,  # Corrected: use session, not subsession
                    case_id=i + 1,
                    points=random.randint(1, 10),
                    is_assigned=False
                )
                cases.append(case)

            # Save case IDs in session vars
            self.session.vars['cases'] = [case.id for case in cases]
        else:
            # Carry over unassigned cases from previous rounds
            cases = Case.filter(session=self.session)
            self.session.vars['cases'] = [
                case.id for case in cases if not case.is_assigned
            ]

        # Create a new judge for each player for the current round
        judges = []
        for player in self.get_players():
            judge = Judge.create(
                session=self.session,  # Corrected: use session, not subsession
                player=player,
                judge_id=player.id + (self.round_number - 1) * 100
            )
            judges.append(judge)

        # Store judge IDs in session vars
        self.session.vars[f'judges_round_{self.round_number}'] = [judge.id for judge in judges]

            
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
    player = models.Link(Player)  # Associate judge with player
    judge_id = models.IntegerField()

class Case(ExtraModel):
    session = models.Link(Session)
    case_id = models.IntegerField()
    points = models.IntegerField()
    is_assigned = models.BooleanField(default=False)  # Track case assignment
    judge = models.Link(Judge)  # Track assigned judge