from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer, ExtraModel
)
import random

author = 'sz'

doc = """
Modeling a greedy algorithm where judges select cases based on associated points.
"""

class Constants(BaseConstants):
    name_in_url = 'greedy_algorithm'
    players_per_group = None
    num_rounds = 10  # Simulate 10 time periods

class Subsession(BaseSubsession):
    def creating_session(self):
        if self.round_number == 1:
            # Create initial cases in round 1
            cases = []
            for i in range(5):
                case = Case.create(
                    subsession=self,
                    case_id=i + 1,
                    points=random.randint(1, 10),
                    is_assigned=False
                )
                cases.append(case)
            # Save case IDs in session.vars
            self.session.vars['cases'] = [case.id for case in cases]
        else:
            # Carry over unassigned cases to the next round
            cases = Case.filter(subsession=self)
            self.session.vars['cases'] = [case.id for case in cases if not case.is_assigned]

        # Simulate new case arrival in every round after the first round
        if self.round_number > 1:
            new_case_arrival = random.choice([True, False])
            if new_case_arrival:
                new_case_id = len(Case.filter(subsession=self)) + 1
                new_case = Case.create(
                    subsession=self,
                    case_id=new_case_id,
                    points=random.randint(1, 10),
                    is_assigned=False
                )
                self.session.vars['cases'].append(new_case.id)

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    # Field to track if the judge has arrived
    arrived = models.BooleanField(initial=False)
    selected_case_ids = models.LongStringField(blank=True)  # Store selected cases as a JSON string

# Use ExtraModel for cases and judges instead of models.Model
class Case(ExtraModel):
    subsession = models.Link(Subsession)  # Link this case to a specific subsession
    case_id = models.IntegerField()  # Unique ID for each case
    points = models.IntegerField(default=0)  # Points associated with the case
    is_assigned = models.BooleanField(default=False)  # Whether the case has been assigned to a judge

class Judge(ExtraModel):
    subsession = models.Link(Subsession)
    judge_id = models.IntegerField()
    arrival_time = models.IntegerField()  # Round number when the judge arrives