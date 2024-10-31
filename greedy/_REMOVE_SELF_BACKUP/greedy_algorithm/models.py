from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer, ExtraModel
)
import random
import json
from otree.models import Session  # Import Session model to link with cases and judges.

class Constants(BaseConstants):
    """
    Defines global constants for the app.
    """
    name_in_url = 'greedy_algorithm'
    players_per_group = None  # No predefined group size.
    num_rounds = 1  # One continuous session, no need to manage rounds.

class Subsession(BaseSubsession):
    """
    Initializes the session with judges and cases.
    """

    def creating_session(self):
        """
        Initializes the cases and judges for the session.
        Cases persist throughout the session and are dynamically updated.
        """
        # Create 5 cases at the start of the session if they don't exist yet
        if not self.session.vars.get('cases'):
            cases = [
                Case.create(
                    session=self.session,
                    case_id=i + 1,
                    points=random.randint(1, 10),
                    is_assigned=False
                ) for i in range(5)
            ]
            self.session.vars['cases'] = [case.id for case in cases]

        # Create a judge for each player if not already created
        if not self.session.vars.get('judges'):
            judges = [
                Judge.create(
                    session=self.session,
                    player=player,
                    judge_id=player.id_in_group
                ) for player in self.get_players()
            ]
            self.session.vars['judges'] = [judge.id for judge in judges]

class Group(BaseGroup):
    """
    Group-level data is not used in this setup.
    """
    pass

class Player(BasePlayer):
    """
    Stores information about players and their selected cases.
    """
    arrived = models.BooleanField(initial=False)
    selected_case_ids = models.LongStringField(blank=True, default='[]')

    @property
    def selected_cases_list(self):
        """Returns the selected cases as a Python list."""
        return json.loads(self.selected_case_ids)

    @selected_cases_list.setter
    def selected_cases_list(self, value):
        """Updates the selected cases with a JSON string."""
        self.selected_case_ids = json.dumps(value)

class Judge(ExtraModel):
    """
    Represents judges, each linked to a player and a session.
    """
    session = models.Link(Session)  # Links the judge to a session.
    player = models.Link(Player)  # Links the judge to a player.
    judge_id = models.IntegerField()  # Unique ID for the judge.

class Case(ExtraModel):
    """
    Represents a case in the experiment.
    """
    session = models.Link(Session)  # Links the case to a session.
    case_id = models.IntegerField()  # Unique ID for the case.
    points = models.IntegerField()  # Points associated with the case.
    is_assigned = models.BooleanField(default=False)  # Tracks if the case is assigned.
    judge = models.Link(Judge)  # Tracks which judge selects the case.