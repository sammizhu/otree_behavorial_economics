from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer, ExtraModel
)
import random

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
                    subsession=self,
                    case_id=i + 1,
                    points=random.randint(1, 10),
                    is_assigned=False
                )
                cases.append(case)

            # Create judges for each player in the first round and link to the player
            for player in self.get_players():
                judge = Judge.create(
                    subsession=self,
                    player=player,  # Link judge to the current player
                    judge_id=player.id  # Use player's id as judge_id
                )
                judges.append(judge)

            # Save case IDs in session.vars
            self.session.vars['cases'] = [case.id for case in cases]
            self.session.vars['judges'] = [judge.id for judge in judges]

        else:
            # Carry over unassigned cases to the next round
            cases = Case.filter(subsession=self)
            self.session.vars['cases'] = [case.id for case in cases if not case.is_assigned]

            # Carry over existing judges to the next round
            judges = Judge.filter(subsession=self)
            self.session.vars['judges'] = [judge.id for judge in judges]

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    arrived = models.BooleanField(initial=False)
    selected_case_ids = models.LongStringField(blank=True)  # Store as JSON string

    def selected_cases_list(self):
        """
        Convert the JSON string into a list of integers.
        Returns an empty list if the string is blank.
        """
        if self.selected_case_ids:
            return json.loads(self.selected_case_ids)
        return []

class Judge(ExtraModel):
    subsession = models.Link(Subsession)
    judge_id = models.IntegerField()
    player = models.Link(Player)  # Link each judge to a Player

class Case(ExtraModel):
    subsession = models.Link(Subsession)  # Link this case to a specific subsession
    judge = models.Link(Judge)  # Make the link optional by using `default=None`
    case_id = models.IntegerField()  # Unique ID for each case
    points = models.IntegerField(default=0)  # Points associated with the case
    is_assigned = models.BooleanField(default=False)  # Whether the case has been assigned to a judge