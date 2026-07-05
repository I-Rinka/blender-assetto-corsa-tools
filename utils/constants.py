# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


KN5_HEADER_BYTES = b"sc6969"

ASSETTO_CORSA_OBJECTS = (
    r"AC_START_\d+",
    r"AC_PIT_\d+",
    r"AC_TIME_\d+_L",
    r"AC_TIME_\d+_R",
    r"AC_HOTLAP_START_\d+",
    r"AC_OPEN_FINISH_R",
    r"AC_OPEN_FINISH_L",
    r"AC_OPEN_START_L",
    r"AC_OPEN_START_R",
    r"AC_AUDIO_.+",
    r"AC_CREW_\d+",
    r"AC_PIT_\d+",
    r"STEER_HR",
    r"STEER_LR",
    r"WHEEL_LF",
    r"WHEEL_RF",
    r"WHEEL_LR",
    r"WHEEL_RR",
    r"SUSP_LF",
    r"SUSP_RF",
    r"SUSP_LR",
    r"SUSP_RR",
    r"HUB_LF",
    r"HUB_RF",
    r"HUB_LR",
    r"HUB_RR",
    r"DISC_LF",
    r"DISC_RF",
    r"DISC_LR",
    r"DISC_RR",
    r"COCKPIT_HR",
    r"COCKPIT_LR",
    r"CINTURE_ON",
    r"CINTURE_OFF",
    r"MOTORHOOD",
    r"REARHOOD",
    r"REAR_WING",
)

CAR_PART_ROLES = (
    ('NONE', "None", "No car part role assigned"),
    ('STEER_HR', "STEER_HR", "High-resolution steering wheel"),
    ('STEER_LR', "STEER_LR", "Low-resolution steering wheel"),
    ('WHEEL_LF', "WHEEL_LF", "Left front wheel"),
    ('WHEEL_RF', "WHEEL_RF", "Right front wheel"),
    ('WHEEL_LR', "WHEEL_LR", "Left rear wheel"),
    ('WHEEL_RR', "WHEEL_RR", "Right rear wheel"),
    ('SUSP_LF', "SUSP_LF", "Left front suspension"),
    ('SUSP_RF', "SUSP_RF", "Right front suspension"),
    ('SUSP_LR', "SUSP_LR", "Left rear suspension"),
    ('SUSP_RR', "SUSP_RR", "Right rear suspension"),
    ('HUB_LF', "HUB_LF", "Left front hub"),
    ('HUB_RF', "HUB_RF", "Right front hub"),
    ('HUB_LR', "HUB_LR", "Left rear hub"),
    ('HUB_RR', "HUB_RR", "Right rear hub"),
    ('DISC_LF', "DISC_LF", "Left front brake disc"),
    ('DISC_RF', "DISC_RF", "Right front brake disc"),
    ('DISC_LR', "DISC_LR", "Left rear brake disc"),
    ('DISC_RR', "DISC_RR", "Right rear brake disc"),
    ('COCKPIT_HR', "COCKPIT_HR", "High-resolution cockpit"),
    ('COCKPIT_LR', "COCKPIT_LR", "Low-resolution cockpit"),
    ('CINTURE_ON', "CINTURE_ON", "Seatbelt on"),
    ('CINTURE_OFF', "CINTURE_OFF", "Seatbelt off"),
    ('MOTORHOOD', "MOTORHOOD", "Motor hood / bonnet"),
    ('REARHOOD', "REARHOOD", "Rear hood / trunk"),
    ('REAR_WING', "REAR_WING", "Rear wing / spoiler"),
)

CAR_PART_NODE_NAMES = frozenset(role[0] for role in CAR_PART_ROLES if role[0] != 'NONE')

REQUIRED_CAR_PARTS = frozenset(('WHEEL_LF', 'WHEEL_RF', 'WHEEL_LR', 'WHEEL_RR'))
