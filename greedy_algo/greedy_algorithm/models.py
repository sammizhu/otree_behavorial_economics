# models.py

from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer, ExtraModel
)
import random

author = 'Your Name'

doc = """
An oTree app modeling the greedy algorithm where judges select cases based on associated points.
"""

class Constants(BaseConstants):
    name_in_url = 'greedy_algorithm'
    players_per_group = None
    num_rounds = 10  # Simulate 10 time periods

class Subsession(BaseSubsession):
    def creating_session(self):
        if self.round_number == 1:
            # Initialize cases
            cases = []

            # Create initial cases
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
            cases = Case.filter()
            self.session.vars['cases'] = [case.id for case in cases if not case.is_assigned]

        # Simulate new case arrival
        new_case_arrival = random.choice([True, False])
        if new_case_arrival:
            new_case_id = len(Case.filter()) + 1
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
    arrived = models.BooleanField(initial=False)
    selected_case_ids = models.LongStringField(blank=True)  # Store as JSON string

class Case(ExtraModel):
    subsession = models.Link(Subsession)
    case_id = models.IntegerField()
    points = models.IntegerField()
    is_assigned = models.BooleanField(default=False)