# from otree.api import (
#     models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer, ExtraModel
# )
# import random
# import json
# from otree.models import Session  # Import Session model to link judges and cases with a session.

# class Constants(BaseConstants):
#     """
#     Defines global constants for the app, such as URL, number of rounds, and group size.
#     """
#     name_in_url = 'greedy_algorithm'
#     players_per_group = None  # No predefined group size.
#     num_rounds = 5  # Simulate 5 time periods (rounds).

# class Subsession(BaseSubsession):
#     """
#     Handles the session setup and data creation logic for each round.
#     """

#     def creating_session(self):
#         """
#         Initializes cases and judges at the beginning of the session. 
#         Cases are created only in the first round, while unassigned cases carry over in subsequent rounds.
#         Judges are created for each player at every round.
#         """
#         cases = []

#         # Create cases only in the first round
#         if self.round_number == 1:
#             for i in range(5):
#                 case = Case.create(
#                     session=self.session,  # Corrected: use session, not subsession
#                     case_id=i + 1,
#                     points=random.randint(1, 10),
#                     is_assigned=False
#                 )
#                 cases.append(case)

#             # Save case IDs in session vars
#             self.session.vars['cases'] = [case.id for case in cases]
#         else:
#             # Carry over unassigned cases from previous rounds
#             cases = Case.filter(session=self.session)
#             self.session.vars['cases'] = [
#                 case.id for case in cases if not case.is_assigned
#             ]

#         # Create a new judge for each player for the current round
#         judges = []
#         for player in self.get_players():
#             judge = Judge.create(
#                 session=self.session,  # Corrected: use session, not subsession
#                 player=player,
#                 judge_id=player.id + (self.round_number - 1) * 100
#             )
#             judges.append(judge)

#         # Store judge IDs in session vars
#         self.session.vars[f'judges_round_{self.round_number}'] = [judge.id for judge in judges]

# class Group(BaseGroup):
#     """
#     A placeholder for group-level data, which is not used in this setup.
#     """
#     pass

# class Player(BasePlayer):
#     """
#     Represents a player in the experiment, tracking arrival status and selected cases.
#     """
#     arrived = models.BooleanField(initial=False)  # Indicates if the player has arrived.
#     selected_case_ids = models.LongStringField(blank=True)  # Stores selected case IDs in JSON format.

#     @property
#     def selected_cases_list(self):
#         """
#         Returns the selected cases as a list by decoding the JSON string.
#         """
#         if self.selected_case_ids:
#             return json.loads(self.selected_case_ids)
#         return []

#     @selected_cases_list.setter
#     def selected_cases_list(self, value):
#         """
#         Sets the selected case IDs by encoding the list as a JSON string.
#         """
#         self.selected_case_ids = json.dumps(value)

# class Judge(ExtraModel):
#     """
#     Stores information about judges, linking them to players and sessions.
#     """
#     session = models.Link(Session)  # Links the judge to a session.
#     player = models.Link(Player)  # Associates the judge with a specific player.
#     judge_id = models.IntegerField()  # Unique ID for the judge.

# class Case(ExtraModel):
#     """
#     Represents a case in the experiment, tracking assignment status and points.
#     """
#     session = models.Link(Session)  # Links the case to a session.
#     case_id = models.IntegerField()  # Unique ID for the case.
#     points = models.IntegerField()  # Points associated with the case.
#     is_assigned = models.BooleanField(default=False)  # Tracks whether the case is assigned.
#     judge = models.Link(Judge)  # Links the case to the judge that selects it.