"""
D&D 5e Character Creation Agent

This program uses a LangChain agent to interactively help users create
complete D&D 5e characters following Player's Handbook (PHB) rules only.
"""

import os
from dotenv import load_dotenv
import random
import json
from typing import Dict, List, Optional, Tuple, Any
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

# ============================================================================
# PHB RULE DATA (Player's Handbook Only)
# ============================================================================

# PHB Classes with their features
# Contains all 12 core classes from D&D 5e Player's Handbook with:
# - Hit dice, saving throw proficiencies, skill choices
# - Starting equipment options
# - Class features by level
PHB_CLASSES = {
    "Barbarian": {
        "hit_die": "d12",
        "saving_throws": ["Strength", "Constitution"],
        "skill_choices": 2,
        "skills": ["Animal Handling", "Athletics", "Intimidation", "Nature", "Perception", "Survival"],
        "armor": ["Light armor", "Medium armor", "Shields"],
        "weapons": ["Simple weapons", "Martial weapons"],
        "tools": [],
        "starting_equipment": {
            "options": [
                "(a) a greataxe or (b) any martial melee weapon",
                "(a) two handaxes or (b) any simple weapon",
                "An explorer's pack and four javelins"
            ]
        },
        "features": {
            1: ["Rage", "Unarmored Defense"],
            2: ["Reckless Attack", "Danger Sense"],
            3: ["Primal Path", "Primal Knowledge"],
        }
    },
    "Bard": {
        "hit_die": "d8",
        "saving_throws": ["Dexterity", "Charisma"],
        "skill_choices": 3,
        "skills": ["Athletics", "Acrobatics", "Sleight of Hand", "Stealth", "Arcana", "History", "Investigation", "Nature", "Religion", "Animal Handling", "Insight", "Medicine", "Perception", "Survival", "Deception", "Intimidation", "Performance", "Persuasion"],
        "armor": ["Light armor"],
        "weapons": ["Simple weapons", "Hand crossbows", "Longswords", "Rapiers", "Shortswords"],
        "tools": ["Three musical instruments of your choice"],
        "starting_equipment": {
            "options": [
                "(a) a rapier, (b) a longsword, or (c) any simple weapon",
                "(a) a diplomat's pack or (b) an entertainer's pack",
                "(a) a lute or (b) any other musical instrument",
                "Leather armor and a dagger"
            ]
        },
        "features": {
            1: ["Spellcasting", "Bardic Inspiration (d6)"],
            2: ["Jack of All Trades", "Song of Rest (d6)"],
            3: ["Bard College", "Expertise"],
        }
    },
    "Cleric": {
        "hit_die": "d8",
        "saving_throws": ["Wisdom", "Charisma"],
        "skill_choices": 2,
        "skills": ["History", "Insight", "Medicine", "Persuasion", "Religion"],
        "armor": ["Light armor", "Medium armor", "Shields"],
        "weapons": ["Simple weapons"],
        "tools": [],
        "starting_equipment": {
            "options": [
                "(a) a mace or (b) a warhammer (if proficient)",
                "(a) scale mail, (b) leather armor, or (c) chain mail (if proficient)",
                "(a) a light crossbow and 20 bolts or (b) any simple weapon",
                "(a) a priest's pack or (b) an explorer's pack",
                "A shield and a holy symbol"
            ]
        },
        "features": {
            1: ["Spellcasting", "Divine Domain"],
            2: ["Channel Divinity (1/rest)", "Divine Domain feature"],
        }
    },
    "Druid": {
        "hit_die": "d8",
        "saving_throws": ["Intelligence", "Wisdom"],
        "skill_choices": 2,
        "skills": ["Arcana", "Animal Handling", "Insight", "Medicine", "Nature", "Perception", "Religion", "Survival"],
        "armor": ["Light armor", "Medium armor", "Shields (nonmetal)"],
        "weapons": ["Clubs", "Daggers", "Darts", "Javelins", "Maces", "Quarterstaffs", "Scimitars", "Sickles", "Slings", "Spears"],
        "tools": ["Herbalism kit"],
        "starting_equipment": {
            "options": [
                "(a) a wooden shield or (b) any simple weapon",
                "(a) a scimitar or (b) any simple melee weapon",
                "Leather armor, an explorer's pack, and a druidic focus"
            ]
        },
        "features": {
            1: ["Spellcasting", "Druidic"],
            2: ["Wild Shape", "Druid Circle"],
        }
    },
    "Fighter": {
        "hit_die": "d10",
        "saving_throws": ["Strength", "Constitution"],
        "skill_choices": 2,
        "skills": ["Acrobatics", "Animal Handling", "Athletics", "History", "Insight", "Intimidation", "Perception", "Survival"],
        "armor": ["All armor", "Shields"],
        "weapons": ["Simple weapons", "Martial weapons"],
        "tools": [],
        "starting_equipment": {
            "options": [
                "(a) chain mail or (b) leather armor, longbow, and 20 arrows",
                "(a) a martial weapon and a shield or (b) a martial weapon and two martial weapons",
                "(a) a light crossbow and 20 bolts or (b) two handaxes",
                "(a) a dungeoneer's pack or (b) an explorer's pack"
            ]
        },
        "features": {
            1: ["Fighting Style", "Second Wind"],
            2: ["Action Surge (one use)"],
            3: ["Martial Archetype"],
        }
    },
    "Monk": {
        "hit_die": "d8",
        "saving_throws": ["Strength", "Dexterity"],
        "skill_choices": 2,
        "skills": ["Acrobatics", "Athletics", "History", "Insight", "Religion", "Stealth"],
        "armor": [],
        "weapons": ["Simple weapons", "Shortswords"],
        "tools": [],
        "starting_equipment": {
            "options": [
                "(a) a shortsword or (b) any simple weapon",
                "(a) a dungeoneer's pack or (b) an explorer's pack",
                "10 darts"
            ]
        },
        "features": {
            1: ["Unarmored Defense", "Martial Arts"],
            2: ["Ki", "Unarmored Movement"],
            3: ["Monastic Tradition", "Deflect Missiles"],
        }
    },
    "Paladin": {
        "hit_die": "d10",
        "saving_throws": ["Wisdom", "Charisma"],
        "skill_choices": 2,
        "skills": ["Athletics", "Insight", "Intimidation", "Medicine", "Persuasion", "Religion"],
        "armor": ["All armor", "Shields"],
        "weapons": ["Simple weapons", "Martial weapons"],
        "tools": [],
        "starting_equipment": {
            "options": [
                "(a) a martial weapon and a shield or (b) two martial weapons",
                "(a) five javelins or (b) any simple melee weapon",
                "(a) a priest's pack or (b) an explorer's pack",
                "Chain mail and a holy symbol"
            ]
        },
        "features": {
            1: ["Divine Sense", "Lay on Hands"],
            2: ["Fighting Style", "Spellcasting", "Divine Smite"],
            3: ["Divine Health", "Sacred Oath"],
        }
    },
    "Ranger": {
        "hit_die": "d10",
        "saving_throws": ["Strength", "Dexterity"],
        "skill_choices": 3,
        "skills": ["Animal Handling", "Athletics", "Insight", "Investigation", "Nature", "Perception", "Stealth", "Survival"],
        "armor": ["Light armor", "Medium armor", "Shields"],
        "weapons": ["Simple weapons", "Martial weapons"],
        "tools": [],
        "starting_equipment": {
            "options": [
                "(a) scale mail or (b) leather armor",
                "(a) two shortswords or (b) two simple melee weapons",
                "(a) a dungeoneer's pack or (b) an explorer's pack",
                "A longbow and a quiver of 20 arrows"
            ]
        },
        "features": {
            1: ["Favored Enemy", "Natural Explorer"],
            2: ["Fighting Style", "Spellcasting"],
            3: ["Ranger Archetype", "Primeval Awareness"],
        }
    },
    "Rogue": {
        "hit_die": "d8",
        "saving_throws": ["Dexterity", "Intelligence"],
        "skill_choices": 4,
        "skills": ["Acrobatics", "Athletics", "Deception", "Insight", "Intimidation", "Investigation", "Perception", "Performance", "Persuasion", "Sleight of Hand", "Stealth"],
        "armor": ["Light armor"],
        "weapons": ["Simple weapons", "Hand crossbows", "Longswords", "Rapiers", "Shortswords"],
        "tools": ["Thieves' tools"],
        "starting_equipment": {
            "options": [
                "(a) a rapier or (b) a shortsword",
                "(a) a shortbow and quiver of 20 arrows or (b) a shortsword",
                "(a) a burglar's pack, (b) a dungeoneer's pack, or (c) an explorer's pack",
                "Leather armor, two daggers, and thieves' tools"
            ]
        },
        "features": {
            1: ["Expertise", "Sneak Attack (1d6)", "Thieves' Cant"],
            2: ["Cunning Action"],
            3: ["Roguish Archetype"],
        }
    },
    "Sorcerer": {
        "hit_die": "d6",
        "saving_throws": ["Constitution", "Charisma"],
        "skill_choices": 2,
        "skills": ["Arcana", "Deception", "Insight", "Intimidation", "Persuasion", "Religion"],
        "armor": [],
        "weapons": ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light crossbows"],
        "tools": [],
        "starting_equipment": {
            "options": [
                "(a) a light crossbow and 20 bolts or (b) any simple weapon",
                "(a) a component pouch or (b) an arcane focus",
                "(a) a dungeoneer's pack or (b) an explorer's pack",
                "Two daggers"
            ]
        },
        "features": {
            1: ["Spellcasting", "Sorcerous Origin"],
            2: ["Font of Magic"],
            3: ["Metamagic"],
        }
    },
    "Warlock": {
        "hit_die": "d8",
        "saving_throws": ["Wisdom", "Charisma"],
        "skill_choices": 2,
        "skills": ["Arcana", "Deception", "History", "Intimidation", "Investigation", "Nature", "Religion"],
        "armor": ["Light armor"],
        "weapons": ["Simple weapons"],
        "tools": [],
        "starting_equipment": {
            "options": [
                "(a) a light crossbow and 20 bolts or (b) any simple weapon",
                "(a) a component pouch or (b) an arcane focus",
                "(a) a scholar's pack or (b) a dungeoneer's pack",
                "Leather armor, any simple weapon, and two daggers"
            ]
        },
        "features": {
            1: ["Otherworldly Patron", "Pact Magic"],
            2: ["Eldritch Invocations (2 known)"],
            3: ["Pact Boon"],
        }
    },
    "Wizard": {
        "hit_die": "d6",
        "saving_throws": ["Intelligence", "Wisdom"],
        "skill_choices": 2,
        "skills": ["Arcana", "History", "Insight", "Investigation", "Medicine", "Religion"],
        "armor": [],
        "weapons": ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light crossbows"],
        "tools": [],
        "starting_equipment": {
            "options": [
                "(a) a quarterstaff or (b) a dagger",
                "(a) a component pouch or (b) an arcane focus",
                "(a) a scholar's pack or (b) an explorer's pack",
                "A spellbook"
            ]
        },
        "features": {
            1: ["Spellcasting", "Arcane Recovery"],
            2: ["Arcane Tradition"],
        }
    }
}

# PHB Backgrounds
PHB_BACKGROUNDS = {
    "Acolyte": {
        "skill_proficiencies": ["Insight", "Religion"],
        "languages": ["Two of your choice"],
        "equipment": ["A holy symbol", "A prayer book or prayer wheel", "5 sticks of incense", "Vestments", "A set of common clothes", "A belt pouch containing 15 gp"],
        "feature": "Shelter of the Faithful",
        "personality_traits": [
            "I idolize a particular hero of my faith and constantly refer to that person's deeds and example.",
            "I can find common ground between the fiercest enemies, empathizing with them and always working toward peace.",
            "I see omens in every event and action. The gods try to speak to us, we just need to listen.",
            "Nothing can shake my optimistic attitude.",
            "I quote (or misquote) sacred texts and proverbs in almost every situation.",
            "I am tolerant (or intolerant) of other faiths and respect (or condemn) the worship of other gods.",
            "I've enjoyed fine food, drink, and high society among my temple's elite. Rough living grates on me.",
            "I've spent so long in the temple that I have little practical experience dealing with people in the outside world."
        ],
        "ideals": [
            "Tradition. The ancient traditions of worship and sacrifice must be preserved and upheld. (Lawful)",
            "Charity. I always try to help those in need, no matter what the personal cost. (Good)",
            "Change. We must help bring about the changes the gods are constantly working in the world. (Chaotic)",
            "Power. I hope to one day rise to the top of my faith's religious hierarchy. (Lawful)",
            "Faith. I trust that my deity will guide my actions. I have faith that if I work hard, things will go well. (Lawful)",
            "Aspiration. I seek to prove myself worthy of my god's favor by matching my actions against their teachings. (Any)"
        ],
        "bonds": [
            "I would die to recover an ancient relic of my faith that was lost long ago.",
            "I will someday get revenge on the corrupt temple hierarchy who branded me a heretic.",
            "I owe my life to the priest who took me in when my parents died.",
            "Everything I do is for the common people.",
            "I will do anything to protect the temple where I served.",
            "I seek to preserve a sacred text that my enemies consider heretical and seek to destroy."
        ],
        "flaws": [
            "I judge others harshly, and myself even more severely.",
            "I put too much trust in those who wield power within my temple's hierarchy.",
            "My piety sometimes leads me to blindly trust those that profess faith in my god.",
            "I am inflexible in my thinking.",
            "I am suspicious of strangers and expect the worst of them.",
            "Once I pick a goal, I become obsessed with it to the detriment of everything else in my life."
        ]
    },
    "Criminal": {
        "skill_proficiencies": ["Deception", "Stealth"],
        "tool_proficiencies": ["One type of gaming set", "Thieves' tools"],
        "equipment": ["A crowbar", "A set of dark common clothes including a hood", "A belt pouch containing 15 gp"],
        "feature": "Criminal Contact",
        "personality_traits": [
            "I always have a plan for what to do when things go wrong.",
            "I am always calm, no matter what the situation. I never raise my voice or let my emotions control me.",
            "The first thing I do in a new place is note the locations of everything valuable—or where such things could be hidden.",
            "I would rather make a new friend than a new enemy.",
            "I am incredibly slow to trust. Those who seem the fairest often have the most to hide.",
            "I don't pay attention to the risks in a situation. Never tell me the odds.",
            "The best way to get me to do something is to tell me I can't do it.",
            "I blow up at the slightest insult."
        ],
        "ideals": [
            "Honor. I don't steal from others in the trade. (Lawful)",
            "Freedom. Chains are meant to be broken, as are those who would forge them. (Chaotic)",
            "Charity. I steal from the wealthy so that I can help people in need. (Good)",
            "Greed. I will do whatever it takes to become wealthy. (Evil)",
            "People. I'm loyal to my friends, not to any ideals, and everyone else can take a trip down the Styx for all I care. (Neutral)",
            "Redemption. There's a spark of good in everyone. (Good)"
        ],
        "bonds": [
            "I'm trying to pay off an old debt I owe to a generous benefactor.",
            "My ill-gotten gains go to support my family.",
            "Something important was taken from me, and I aim to steal it back.",
            "I will become the greatest thief that ever lived.",
            "I'm guilty of a terrible crime. I hope I can redeem myself for it.",
            "Someone I loved died because of a mistake I made. That will never happen again."
        ],
        "flaws": [
            "When I see something valuable, I can't think about anything but how to steal it.",
            "When faced with a choice between money and my friends, I usually choose the money.",
            "If there's a plan, I'll forget it. If I don't forget it, I'll ignore it.",
            "I have a 'tell' that reveals when I'm lying.",
            "I turn tail and run when things look bad.",
            "An innocent person is in prison for a crime that I committed. I'm okay with that."
        ]
    },
    "Folk Hero": {
        "skill_proficiencies": ["Animal Handling", "Survival"],
        "tool_proficiencies": ["One type of artisan's tools", "Vehicles (land)"],
        "equipment": ["A set of artisan's tools (one of your choice)", "A shovel", "An iron pot", "A set of common clothes", "A belt pouch containing 10 gp"],
        "feature": "Rustic Hospitality",
        "personality_traits": [
            "I judge people by their actions, not their words.",
            "If someone is in trouble, I'm always ready to lend help.",
            "When I set my mind to something, I follow through no matter what gets in my way.",
            "I have a strong sense of fair play and always try to find the most equitable solution to arguments.",
            "I'm confident in my own abilities and do what I can to instill confidence in others.",
            "Thinking is for other people. I prefer action.",
            "I misuse long words in an attempt to sound smarter.",
            "I get bored easily. When am I going to get on with my destiny?"
        ],
        "ideals": [
            "Respect. People deserve to be treated with dignity and respect. (Good)",
            "Fairness. No one should get preferential treatment before the law, and no one is above the law. (Lawful)",
            "Freedom. Tyrants must not be allowed to oppress the people. (Chaotic)",
            "Might. If I become strong, I will take what I want—what I deserve. (Evil)",
            "Sincerity. There's no good in pretending to be something I'm not. (Neutral)",
            "Destiny. Nothing and no one can steer me away from my higher calling. (Any)"
        ],
        "bonds": [
            "I have a family, but I have no idea where they are. One day, I hope to see them again.",
            "I worked the land, I love the land, and I will protect the land.",
            "A proud noble once gave me a horrible beating, and I will take my revenge on any bully I encounter.",
            "My tools are symbols of my past life, and I carry them so that I will never forget my roots.",
            "I protect those who cannot protect themselves.",
            "I wish my childhood sweetheart had come with me to pursue my destiny."
        ],
        "flaws": [
            "The tyrant who rules my land will stop at nothing to see me killed.",
            "I'm convinced of the significance of my destiny, and blind to my shortcomings and the risk of failure.",
            "The people who knew me when I was young know my shameful secret, so I can never go home again.",
            "I have a weakness for the vices of the city, especially hard drink.",
            "Secretly, I believe that things would be better if I were a tyrant lording over the land.",
            "I have trouble trusting in my allies."
        ]
    },
    "Noble": {
        "skill_proficiencies": ["History", "Persuasion"],
        "tool_proficiencies": ["One type of gaming set"],
        "languages": ["One of your choice"],
        "equipment": ["Fine clothes", "A signet ring", "A scroll of pedigree", "A purse containing 25 gp"],
        "feature": "Position of Privilege",
        "personality_traits": [
            "My eloquent flattery makes everyone I talk to feel like the most wonderful and important person in the world.",
            "The common folk love me for my kindness and generosity.",
            "No one could doubt by looking at my regal bearing that I am a cut above the unwashed masses.",
            "I take great pains to always look my best and follow the latest fashions.",
            "I don't like to get my hands dirty, and I won't be caught dead in unsuitable accommodations.",
            "Despite my noble birth, I do not place myself above other folk. We all have the same blood.",
            "My favor, once lost, is lost forever.",
            "If you do me an injury, I will crush you, ruin your name, and salt your fields."
        ],
        "ideals": [
            "Respect. Respect is due to me because of my position, but all people regardless of station deserve to be treated with dignity. (Good)",
            "Responsibility. It is my duty to respect the authority of those above me, just as those below me must respect mine. (Lawful)",
            "Independence. I must prove that I can handle myself without the coddling of my family. (Chaotic)",
            "Power. If I can attain more power, no one will tell me what to do. (Evil)",
            "Family. Blood runs thicker than water. (Any)",
            "Noble Obligation. It is my duty to protect and care for the people beneath me. (Good)"
        ],
        "bonds": [
            "I will face any challenge to win the approval of my family.",
            "My house's alliance with another noble family must be sustained at all costs.",
            "Nothing is more important than the other members of my family.",
            "I am in love with the heir of a family that my family despises.",
            "My loyalty to my sovereign is unwavering.",
            "The common folk must see me as a hero of the people."
        ],
        "flaws": [
            "I secretly believe that everyone is beneath me.",
            "I hide a truly scandalous secret that could ruin my family forever.",
            "I too often hear veiled insults and threats in every word addressed to me, and I'm quick to anger.",
            "I have an insatiable desire for carnal pleasures.",
            "In fact, the world does revolve around me.",
            "By my words and actions, I often bring shame to my family."
        ]
    },
    "Sage": {
        "skill_proficiencies": ["Arcana", "History"],
        "languages": ["Two of your choice"],
        "equipment": ["A bottle of black ink", "A quill", "A small knife", "A letter from a dead colleague posing a question you have not yet been able to answer", "A set of common clothes", "A belt pouch containing 10 gp"],
        "feature": "Researcher",
        "personality_traits": [
            "I use polysyllabic words that convey the impression of great erudition.",
            "I've read every book in the world's greatest libraries—or I like to boast that I have.",
            "I'm used to helping out those who aren't as smart as I am, and I patiently explain anything and everything to others.",
            "There's nothing I like more than a good mystery.",
            "I'm willing to listen to every side of an argument before I make my own judgment.",
            "I... speak... slowly... when talking... to idiots... which... almost... everyone... is... compared... to me.",
            "I am horribly, horribly awkward in social situations.",
            "I'm convinced that people are always trying to steal my secrets."
        ],
        "ideals": [
            "Knowledge. The path to power and self-improvement is through knowledge. (Neutral)",
            "Beauty. What is beautiful points us beyond itself toward what is true. (Good)",
            "Logic. Emotions must not cloud our logical thinking. (Lawful)",
            "No Limits. Nothing should fetter the infinite possibility inherent in all existence. (Chaotic)",
            "Power. Knowledge is the path to power and domination. (Evil)",
            "Self-Improvement. The goal of a life of study is the betterment of oneself. (Any)"
        ],
        "bonds": [
            "It is my duty to protect my students.",
            "I have an ancient text that holds terrible secrets that must not fall into the wrong hands.",
            "I work to preserve a library, university, scriptorium, or monastery.",
            "My life's work is a series of tomes related to a specific field of lore.",
            "I've been searching my whole life for the answer to a certain question.",
            "I sold my soul for knowledge. I hope to do great deeds and win it back."
        ],
        "flaws": [
            "I am easily distracted by the promise of information.",
            "Most people scream and run when they see a demon. I stop and take notes on its anatomy.",
            "Unlocking an ancient mystery is worth the price of a civilization.",
            "I overlook obvious solutions in favor of complicated ones.",
            "I speak without really thinking through my words, invariably insulting others.",
            "I can't keep a secret to save my life, or anyone else's."
        ]
    },
    "Soldier": {
        "skill_proficiencies": ["Athletics", "Intimidation"],
        "tool_proficiencies": ["One type of gaming set", "Vehicles (land)"],
        "equipment": ["An insignia of rank", "A trophy taken from a fallen enemy", "A set of bone dice or deck of cards", "A set of common clothes", "A belt pouch containing 10 gp"],
        "feature": "Military Rank",
        "personality_traits": [
            "I'm always polite and respectful.",
            "I'm haunted by memories of war. I can't get the images of violence out of my mind.",
            "I've lost too many friends, and I'm slow to make new ones.",
            "I'm full of inspiring and cautionary tales from my military experience relevant to almost every combat situation.",
            "I can stare down a hell hound without flinching.",
            "I enjoy being strong and like breaking things.",
            "I have a crude sense of humor.",
            "I face problems head-on. A simple, direct solution is the best path to success."
        ],
        "ideals": [
            "Greater Good. Our lot is to lay down our lives in defense of others. (Good)",
            "Responsibility. I do what I must and obey just authority. (Lawful)",
            "Independence. When people follow orders blindly, they embrace a kind of tyranny. (Chaotic)",
            "Might. In life as in war, the stronger force wins. (Evil)",
            "Live and Let Live. Ideals aren't worth killing over or going to war for. (Neutral)",
            "Nation. My city, nation, or people are all that matter. (Any)"
        ],
        "bonds": [
            "I would still lay down my life for the people I served with.",
            "Someone saved my life on the battlefield. To this day, I will never leave a friend behind.",
            "My honor is my life.",
            "I'll never forget the crushing defeat my company suffered or the enemies who dealt it.",
            "Those who fight beside me are those worth dying for.",
            "I fight for those who cannot fight for themselves."
        ],
        "flaws": [
            "The monstrous enemy we faced in battle still leaves me quivering with fear.",
            "I have little respect for anyone who is not a proven warrior.",
            "I made a terrible mistake in battle that cost many lives—and I would do anything to keep that mistake secret.",
            "My hatred of my enemies is blind and unreasoning.",
            "I obey the law, even if the law causes misery.",
            "I'd rather eat my armor than admit when I'm wrong."
        ]
    },
    "Urchin": {
        "skill_proficiencies": ["Sleight of Hand", "Stealth"],
        "tool_proficiencies": ["Disguise kit", "Thieves' tools"],
        "equipment": ["A small knife", "A map of the city you grew up in", "A pet mouse", "A token to remember your parents by", "A set of common clothes", "A belt pouch containing 10 gp"],
        "feature": "City Secrets",
        "personality_traits": [
            "I hide scraps of food and trinkets away in my pockets.",
            "I ask a lot of questions.",
            "I like to squeeze into small places where no one else can get to me.",
            "I sleep with my back to a wall or tree, with everything I own wrapped in a bundle in my arms.",
            "I eat like a pig and have bad manners.",
            "I think anyone who's nice to me is hiding evil intent.",
            "I don't like to bathe.",
            "I bluntly say what other people are hinting at or hiding."
        ],
        "ideals": [
            "Respect. All people, rich or poor, deserve respect. (Good)",
            "Community. We have to take care of each other, because no one else is going to do it. (Lawful)",
            "Change. The low are lifted up, and the high and mighty are brought down. Change is the nature of things. (Chaotic)",
            "Retribution. The rich need to be shown what life and death are like in the gutters. (Evil)",
            "People. I help the people who help me—that's what keeps us alive. (Neutral)",
            "Aspiration. I'm going to prove that I'm worthy of a better life. (Any)"
        ],
        "bonds": [
            "My town or city is my home, and I'll fight to defend it.",
            "I sponsor an orphanage to keep others from enduring what I was forced to endure.",
            "I owe my survival to another urchin who taught me to live on the streets.",
            "I owe a debt I can never repay to the person who took pity on me.",
            "I escaped my life of poverty by robbing an important person, and I'm wanted for it.",
            "No one else should have to endure the hardships I've been through."
        ],
        "flaws": [
            "If I'm outnumbered, I will run away from a fight.",
            "Gold seems like a lot of money to me, and I'll do just about anything for more of it.",
            "I will never fully trust anyone other than myself.",
            "I'd rather kill someone in their sleep than fight fair.",
            "It's not stealing if I need it more than someone else.",
            "People who can't take care of themselves get what they deserve."
        ]
    }
}

# PHB Species (Races) with ability score increases and traits
PHB_SPECIES = {
    "Human": {
        "ability_score_increases": {"Strength": 1, "Dexterity": 1, "Constitution": 1, "Intelligence": 1, "Wisdom": 1, "Charisma": 1},
        "size": "Medium",
        "speed": 30,
        "languages": ["Common", "One extra language of your choice"],
        "traits": ["Extra Language", "Extra Skill Proficiency"]
    },
    "Dwarf": {
        "subspecies": ["Hill Dwarf", "Mountain Dwarf"],
        "ability_score_increases_base": {"Constitution": 2},
        "size": "Medium",
        "speed": 25,
        "languages": ["Common", "Dwarvish"],
        "traits": ["Darkvision (60 ft)", "Dwarven Resilience", "Dwarven Combat Training", "Stonecunning"],
        "Hill Dwarf": {
            "ability_score_increases": {"Wisdom": 1},
            "traits": ["Dwarven Toughness"]
        },
        "Mountain Dwarf": {
            "ability_score_increases": {"Strength": 2},
            "traits": ["Dwarven Armor Training"]
        }
    },
    "Elf": {
        "subspecies": ["High Elf", "Wood Elf", "Drow"],
        "ability_score_increases_base": {"Dexterity": 2},
        "size": "Medium",
        "speed": 30,
        "languages": ["Common", "Elvish"],
        "traits": ["Darkvision (60 ft)", "Keen Senses", "Fey Ancestry", "Trance"],
        "High Elf": {
            "ability_score_increases": {"Intelligence": 1},
            "traits": ["Elf Weapon Training", "Cantrip", "Extra Language"]
        },
        "Wood Elf": {
            "ability_score_increases": {"Wisdom": 1},
            "traits": ["Elf Weapon Training", "Fleet of Foot", "Mask of the Wild"]
        },
        "Drow": {
            "ability_score_increases": {"Charisma": 1},
            "traits": ["Superior Darkvision (120 ft)", "Sunlight Sensitivity", "Drow Magic"]
        }
    },
    "Halfling": {
        "subspecies": ["Lightfoot", "Stout"],
        "ability_score_increases_base": {"Dexterity": 2},
        "size": "Small",
        "speed": 25,
        "languages": ["Common", "Halfling"],
        "traits": ["Lucky", "Brave", "Halfling Nimbleness"],
        "Lightfoot": {
            "ability_score_increases": {"Charisma": 1},
            "traits": ["Naturally Stealthy"]
        },
        "Stout": {
            "ability_score_increases": {"Constitution": 1},
            "traits": ["Stout Resilience"]
        }
    },
    "Dragonborn": {
        "ability_score_increases": {"Strength": 2, "Charisma": 1},
        "size": "Medium",
        "speed": 30,
        "languages": ["Common", "Draconic"],
        "traits": ["Draconic Ancestry", "Breath Weapon", "Damage Resistance"]
    },
    "Gnome": {
        "subspecies": ["Forest Gnome", "Rock Gnome"],
        "ability_score_increases_base": {"Intelligence": 2},
        "size": "Small",
        "speed": 25,
        "languages": ["Common", "Gnomish"],
        "traits": ["Darkvision (60 ft)", "Gnome Cunning"],
        "Forest Gnome": {
            "ability_score_increases": {"Dexterity": 1},
            "traits": ["Natural Illusionist", "Speak with Small Beasts"]
        },
        "Rock Gnome": {
            "ability_score_increases": {"Constitution": 1},
            "traits": ["Artificer's Lore", "Tinker"]
        }
    },
    "Half-Elf": {
        "ability_score_increases": {"Charisma": 2},
        "ability_score_increases_choice": {"Two different abilities": 1},
        "size": "Medium",
        "speed": 30,
        "languages": ["Common", "Elvish", "One extra language of your choice"],
        "traits": ["Darkvision (60 ft)", "Fey Ancestry", "Skill Versatility (two skills)"]
    },
    "Half-Orc": {
        "ability_score_increases": {"Strength": 2, "Constitution": 1},
        "size": "Medium",
        "speed": 30,
        "languages": ["Common", "Orc"],
        "traits": ["Darkvision (60 ft)", "Menacing", "Relentless Endurance", "Savage Attacks"]
    },
    "Tiefling": {
        "ability_score_increases": {"Intelligence": 1, "Charisma": 2},
        "size": "Medium",
        "speed": 30,
        "languages": ["Common", "Infernal"],
        "traits": ["Darkvision (60 ft)", "Hellish Resistance", "Infernal Legacy"]
    }
}

# Alignments
ALIGNMENTS = [
    "Lawful Good", "Neutral Good", "Chaotic Good",
    "Lawful Neutral", "True Neutral", "Chaotic Neutral",
    "Lawful Evil", "Neutral Evil", "Chaotic Evil"
]

# ============================================================================
# CHARACTER DATA MODEL
# ============================================================================

# Global character data structure (used by agent tools)
# This stores the current character being created in a session
character_data: Dict[str, Any] = {
    "name": None,
    "class": None,
    "level": 1,
    "species": None,
    "subspecies": None,
    "background": None,
    "alignment": None,
    "experience_points": 0,
    "ability_scores": {
        "Strength": None,
        "Dexterity": None,
        "Constitution": None,
        "Intelligence": None,
        "Wisdom": None,
        "Charisma": None
    },
    "ability_modifiers": {
        "Strength": None,
        "Dexterity": None,
        "Constitution": None,
        "Intelligence": None,
        "Wisdom": None,
        "Charisma": None
    },
    "saving_throw_proficiencies": [],
    "skill_proficiencies": [],
    "armor_proficiencies": [],
    "weapon_proficiencies": [],
    "tool_proficiencies": [],
    "language_proficiencies": [],
    "passive_perception": None,
    "passive_investigation": None,
    "passive_insight": None,
    "armor_class": None,
    "initiative": None,
    "speed": None,
    "hit_points": None,
    "hit_dice": None,
    "equipment": [],
    "personality_trait": None,
    "ideal": None,
    "bond": None,
    "flaw": None,
    "background_feature": None,
    "class_features": [],
    "subclass": None,
    "species_traits": [],
    "age": None,
    "height": None,
    "weight": None,
    "eyes": None,
    "skin": None,
    "hair": None,
    "backstory": None,
    "generation_method": None
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# Point buy cost table for 27-point variant
# Each ability score from 8-15 has an associated point cost
POINT_BUY_COSTS = {
    8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9
}

# Standard array
STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

# XP by level
XP_BY_LEVEL = {
    1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500, 6: 14000, 7: 23000, 8: 34000,
    9: 48000, 10: 64000, 11: 85000, 12: 100000, 13: 120000, 14: 140000,
    15: 165000, 16: 195000, 17: 225000, 18: 265000, 19: 305000, 20: 355000
}


def calculate_ability_modifier(score: int) -> int:
    """Calculate the ability modifier for a given ability score.
    
    Formula: (score - 10) // 2
    """
    return (score - 10) // 2


def roll_4d6_drop_lowest() -> int:
    """Roll 4d6 and drop the lowest die."""
    rolls = [random.randint(1, 6) for _ in range(4)]
    rolls.sort()
    return sum(rolls[1:])


def calculate_hit_points(class_name: str, level: int, constitution_modifier: int) -> Tuple[int, str]:
    """Calculate hit points based on class, level, and Constitution modifier.
    
    First level: max hit die + CON mod
    Subsequent levels: average of hit die (rounded up) + CON mod
    """
    hit_die_map = {
        "Barbarian": 12, "Fighter": 10, "Paladin": 10, "Ranger": 10,
        "Bard": 8, "Cleric": 8, "Druid": 8, "Monk": 8, "Rogue": 8, "Warlock": 8,
        "Sorcerer": 6, "Wizard": 6
    }
    
    hit_die = hit_die_map.get(class_name, 8)
    hp_per_level = (hit_die // 2) + 1  # Average rounded up
    
    if level == 1:
        total_hp = hit_die + constitution_modifier
    else:
        total_hp = hit_die + constitution_modifier + (hp_per_level * (level - 1))
    
    hit_dice_str = f"{level}d{hit_die}"
    
    return max(1, total_hp), hit_dice_str


def calculate_armor_class(dexterity_modifier: int, armor: str = None) -> int:
    """Calculate Armor Class.
    
    Default: 10 + DEX mod (unarmored)
    With armor: depends on armor type (simplified for now)
    """
    if armor:
        # Simplified armor calculations
        if "leather" in armor.lower():
            return 11 + min(dexterity_modifier, 0)  # Max DEX mod applies
        elif "chain" in armor.lower() or "scale" in armor.lower():
            return 16  # No DEX mod for heavy armor
        elif "studded" in armor.lower():
            return 12 + min(dexterity_modifier, 0)
    return 10 + dexterity_modifier


def calculate_passive_skill(ability_modifier: int, proficiency_bonus: int, has_proficiency: bool) -> int:
    """Calculate passive skill score (10 + ability mod + proficiency if proficient)."""
    base = 10 + ability_modifier
    if has_proficiency:
        base += proficiency_bonus
    return base


def get_proficiency_bonus(level: int) -> int:
    """Get proficiency bonus based on level."""
    return 2 + ((level - 1) // 4)


def apply_species_ability_increases(base_scores: Dict[str, int], species: str, subspecies: str = None) -> Dict[str, int]:
    """Apply species ability score increases to base scores."""
    scores = base_scores.copy()
    
    if species not in PHB_SPECIES:
        return scores
    
    species_data = PHB_SPECIES[species]
    
    # Apply base increases
    if "ability_score_increases_base" in species_data:
        for ability, increase in species_data["ability_score_increases_base"].items():
            scores[ability] = scores.get(ability, 0) + increase
    
    # Apply species-specific increases
    if "ability_score_increases" in species_data:
        for ability, increase in species_data["ability_score_increases"].items():
            scores[ability] = scores.get(ability, 0) + increase
    
    # Apply subspecies increases
    if subspecies and subspecies in species_data:
        if "ability_score_increases" in species_data[subspecies]:
            for ability, increase in species_data[subspecies]["ability_score_increases"].items():
                scores[ability] = scores.get(ability, 0) + increase
    
    return scores


def get_species_speed(species: str, subspecies: str = None) -> int:
    """Get speed for species."""
    if species in PHB_SPECIES:
        base_speed = PHB_SPECIES[species].get("speed", 30)
        # Wood Elf has +5 speed
        if species == "Elf" and subspecies == "Wood Elf":
            return base_speed + 5
        return base_speed
    return 30


# ============================================================================
# LANGCHAIN TOOLS
# ============================================================================

# These functions are decorated with @tool to make them available to the
# LangChain agent. The agent can call these tools to perform character
# creation operations based on user input.

@tool
def roll_ability_scores() -> str:
    """Roll ability scores using the standard 4d6 drop lowest method.
    
    This generates six ability scores by rolling 4d6 and dropping the lowest
    die for each score. This simulates the traditional rolling method.
    
    Returns:
        A formatted string showing all six ability scores and their modifiers.
    """
    scores = {}
    modifiers = {}
    
    for ability in ["Strength", "Dexterity", "Constitution", 
                    "Intelligence", "Wisdom", "Charisma"]:
        score = roll_4d6_drop_lowest()
        scores[ability] = score
        modifiers[ability] = calculate_ability_modifier(score)
    
    # Store in character data
    character_data["ability_scores"] = scores
    character_data["ability_modifiers"] = modifiers
    character_data["generation_method"] = "rolled"
    
    # Format output
    result = "Rolled Ability Scores:\n"
    result += "-" * 40 + "\n"
    for ability in ["Strength", "Dexterity", "Constitution", 
                    "Intelligence", "Wisdom", "Charisma"]:
        score = scores[ability]
        mod = modifiers[ability]
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        result += f"{ability:15} {score:2} (modifier: {mod_str:>3})\n"
    
    return result


@tool
def generate_point_buy_scores(
    strength: int = None,
    dexterity: int = None,
    constitution: int = None,
    intelligence: int = None,
    wisdom: int = None,
    charisma: int = None
) -> str:
    """Generate ability scores using the 27-point buy variant rule.
    
    In point buy, each ability score costs points based on its value:
    - 8 costs 0 points
    - 9 costs 1 point
    - 10 costs 2 points
    - 11 costs 3 points
    - 12 costs 4 points
    - 13 costs 5 points
    - 14 costs 7 points
    - 15 costs 9 points
    
    You have 27 points total to spend. All scores start at 8.
    
    Args:
        strength: Desired Strength score (8-15)
        dexterity: Desired Dexterity score (8-15)
        constitution: Desired Constitution score (8-15)
        intelligence: Desired Intelligence score (8-15)
        wisdom: Desired Wisdom score (8-15)
        charisma: Desired Charisma score (8-15)
    
    Returns:
        A formatted string showing the ability scores, modifiers, and point cost.
    """
    # Default all scores to 8 if not specified
    scores = {
        "Strength": strength if strength is not None else 8,
        "Dexterity": dexterity if dexterity is not None else 8,
        "Constitution": constitution if constitution is not None else 8,
        "Intelligence": intelligence if intelligence is not None else 8,
        "Wisdom": wisdom if wisdom is not None else 8,
        "Charisma": charisma if charisma is not None else 8
    }
    
    # Validate scores are in valid range
    for ability, score in scores.items():
        if score < 8 or score > 15:
            return f"Error: {ability} score of {score} is invalid. Scores must be between 8 and 15 for point buy."
    
    # Calculate total point cost
    total_cost = 0
    modifiers = {}
    for ability, score in scores.items():
        if score not in POINT_BUY_COSTS:
            return f"Error: {ability} score of {score} is invalid. Valid scores for point buy are 8-15."
        total_cost += POINT_BUY_COSTS[score]
        modifiers[ability] = calculate_ability_modifier(score)
    
    # Check if within budget
    if total_cost > 27:
        return f"Error: Total point cost ({total_cost}) exceeds the 27-point budget. Please adjust scores."
    
    # Store in character data
    character_data["ability_scores"] = scores
    character_data["ability_modifiers"] = modifiers
    character_data["generation_method"] = "point_buy"
    
    # Format output
    result = "Point Buy Ability Scores:\n"
    result += "-" * 50 + "\n"
    for ability in ["Strength", "Dexterity", "Constitution", 
                    "Intelligence", "Wisdom", "Charisma"]:
        score = scores[ability]
        mod = modifiers[ability]
        cost = POINT_BUY_COSTS[score]
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        result += f"{ability:15} {score:2} (modifier: {mod_str:>3}, cost: {cost:2} points)\n"
    result += "-" * 50 + "\n"
    result += f"Total points spent: {total_cost} / 27\n"
    
    return result


@tool
def generate_standard_array_scores(
    strength: int = None,
    dexterity: int = None,
    constitution: int = None,
    intelligence: int = None,
    wisdom: int = None,
    charisma: int = None
) -> str:
    """Generate ability scores using the standard array (15, 14, 13, 12, 10, 8).
    
    You assign each score to one ability. The standard array provides balanced scores.
    
    Args:
        strength: Standard array value assigned to Strength
        dexterity: Standard array value assigned to Dexterity
        constitution: Standard array value assigned to Constitution
        intelligence: Standard array value assigned to Intelligence
        wisdom: Standard array value assigned to Wisdom
        charisma: Standard array value assigned to Charisma
    
    Returns:
        A formatted string showing the ability scores and modifiers.
    """
    # Check that all values are provided and valid
    scores = {
        "Strength": strength,
        "Dexterity": dexterity,
        "Constitution": constitution,
        "Intelligence": intelligence,
        "Wisdom": wisdom,
        "Charisma": charisma
    }
    
    # Validate all scores are provided
    if any(s is None for s in scores.values()):
        return "Error: All six ability scores must be assigned from the standard array (15, 14, 13, 12, 10, 8)."
    
    # Validate scores match standard array
    provided_scores = sorted(scores.values(), reverse=True)
    if provided_scores != STANDARD_ARRAY:
        return f"Error: Scores must match the standard array exactly: {STANDARD_ARRAY}. You provided: {provided_scores}"
    
    # Calculate modifiers
    modifiers = {}
    for ability, score in scores.items():
        modifiers[ability] = calculate_ability_modifier(score)
    
    # Store in character data
    character_data["ability_scores"] = scores
    character_data["ability_modifiers"] = modifiers
    character_data["generation_method"] = "standard_array"
    
    # Format output
    result = "Standard Array Ability Scores:\n"
    result += "-" * 40 + "\n"
    for ability in ["Strength", "Dexterity", "Constitution", 
                    "Intelligence", "Wisdom", "Charisma"]:
        score = scores[ability]
        mod = modifiers[ability]
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        result += f"{ability:15} {score:2} (modifier: {mod_str:>3})\n"
    
    return result


@tool
def set_character_name(name: str) -> str:
    """Set the character's name.
    
    Args:
        name: The character's name
    
    Returns:
        Confirmation message with the character's name.
    """
    character_data["name"] = name
    return f"Character name set to: {name}"


@tool
def set_character_class(class_name: str, level: int = 1) -> str:
    """Set the character's class and level.
    
    Valid PHB classes: Barbarian, Bard, Cleric, Druid, Fighter, Monk,
    Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard.
    
    Args:
        class_name: The character's class
        level: The character's level (1-20, default 1)
    
    Returns:
        Confirmation message with class and level information.
    """
    if class_name not in PHB_CLASSES:
        return f"Error: '{class_name}' is not a valid PHB class. Valid classes: {', '.join(PHB_CLASSES.keys())}"
    
    if level < 1 or level > 20:
        return "Error: Level must be between 1 and 20."
    
    character_data["class"] = class_name
    character_data["level"] = level
    character_data["experience_points"] = XP_BY_LEVEL.get(level, 0)
    
    # Apply class features
    class_info = PHB_CLASSES[class_name]
    features = []
    for feat_level in sorted(class_info["features"].keys()):
        if level >= feat_level:
            features.extend(class_info["features"][feat_level])
    character_data["class_features"] = features
    character_data["saving_throw_proficiencies"] = class_info["saving_throws"]
    
    return f"Character class set to: {class_name} (Level {level})"


@tool
def set_character_species(species: str, subspecies: str = None) -> str:
    """Set the character's species (race) and optional subspecies.
    
    Valid PHB species: Human, Dwarf (Hill/Mountain), Elf (High/Wood/Drow),
    Halfling (Lightfoot/Stout), Dragonborn, Gnome (Forest/Rock),
    Half-Elf, Half-Orc, Tiefling.
    
    Args:
        species: The character's species
        subspecies: Optional subspecies (e.g., "Hill Dwarf", "Wood Elf")
    
    Returns:
        Confirmation message with species information.
    """
    if species not in PHB_SPECIES:
        return f"Error: '{species}' is not a valid PHB species. Valid species: {', '.join(PHB_SPECIES.keys())}"
    
    species_data = PHB_SPECIES[species]
    
    # Check if subspecies is valid
    if "subspecies" in species_data:
        if subspecies and subspecies not in species_data["subspecies"]:
            return f"Error: '{subspecies}' is not a valid subspecies for {species}. Valid options: {', '.join(species_data['subspecies'])}"
    elif subspecies:
        return f"Error: {species} does not have subspecies."
    
    character_data["species"] = species
    character_data["subspecies"] = subspecies
    
    # Apply species ability score increases if ability scores are set
    if any(character_data["ability_scores"].values()):
        base_scores = character_data["ability_scores"].copy()
        updated_scores = apply_species_ability_increases(base_scores, species, subspecies)
        character_data["ability_scores"] = updated_scores
        
        # Recalculate modifiers
        for ability, score in updated_scores.items():
            character_data["ability_modifiers"][ability] = calculate_ability_modifier(score)
    
    # Set speed
    character_data["speed"] = get_species_speed(species, subspecies)
    
    # Set species traits
    traits = species_data.get("traits", [])
    if subspecies and subspecies in species_data:
        traits.extend(species_data[subspecies].get("traits", []))
    character_data["species_traits"] = traits
    
    # Set languages
    languages = species_data.get("languages", [])
    character_data["language_proficiencies"] = languages
    
    species_display = f"{subspecies} {species}" if subspecies else species
    return f"Character species set to: {species_display}"


@tool
def set_character_background(background: str) -> str:
    """Set the character's background.
    
    Valid PHB backgrounds: Acolyte, Criminal, Folk Hero, Noble, Sage, Soldier, Urchin.
    
    Args:
        background: The character's background
    
    Returns:
        Confirmation message with background information.
    """
    if background not in PHB_BACKGROUNDS:
        return f"Error: '{background}' is not a valid PHB background. Valid backgrounds: {', '.join(PHB_BACKGROUNDS.keys())}"
    
    character_data["background"] = background
    
    bg_data = PHB_BACKGROUNDS[background]
    
    # Add background skill proficiencies
    if "skill_proficiencies" in bg_data:
        character_data["skill_proficiencies"].extend(bg_data["skill_proficiencies"])
    
    # Add tool proficiencies
    if "tool_proficiencies" in bg_data:
        character_data["tool_proficiencies"].extend(bg_data["tool_proficiencies"])
    
    # Add languages
    if "languages" in bg_data:
        character_data["language_proficiencies"].extend(bg_data["languages"])
    
    # Set background feature
    character_data["background_feature"] = bg_data.get("feature", "")
    
    return f"Character background set to: {background}"


@tool
def set_alignment(alignment: str) -> str:
    """Set the character's alignment.
    
    Valid alignments: Lawful Good, Neutral Good, Chaotic Good,
    Lawful Neutral, True Neutral, Chaotic Neutral,
    Lawful Evil, Neutral Evil, Chaotic Evil.
    
    Args:
        alignment: The character's alignment
    
    Returns:
        Confirmation message with alignment.
    """
    if alignment not in ALIGNMENTS:
        return f"Error: '{alignment}' is not a valid alignment. Valid alignments: {', '.join(ALIGNMENTS)}"
    
    character_data["alignment"] = alignment
    return f"Character alignment set to: {alignment}"


@tool
def set_background_personality(personality_trait: str = None, ideal: str = None, bond: str = None, flaw: str = None) -> str:
    """Set background personality details (trait, ideal, bond, flaw).
    
    These are typically chosen from the background's suggested options,
    but custom options are also valid.
    
    Args:
        personality_trait: A personality trait
        ideal: An ideal
        bond: A bond
        flaw: A flaw
    
    Returns:
        Confirmation message.
    """
    if personality_trait:
        character_data["personality_trait"] = personality_trait
    if ideal:
        character_data["ideal"] = ideal
    if bond:
        character_data["bond"] = bond
    if flaw:
        character_data["flaw"] = flaw
    
    result = "Background personality details updated:\n"
    if personality_trait:
        result += f"  Trait: {personality_trait}\n"
    if ideal:
        result += f"  Ideal: {ideal}\n"
    if bond:
        result += f"  Bond: {bond}\n"
    if flaw:
        result += f"  Flaw: {flaw}\n"
    
    return result.strip()


@tool
def set_physical_description(age: int = None, height: str = None, weight: str = None, 
                             eyes: str = None, skin: str = None, hair: str = None) -> str:
    """Set optional physical description details.
    
    Args:
        age: Character's age
        height: Character's height
        weight: Character's weight
        eyes: Eye color
        skin: Skin color/description
        hair: Hair color/description
    
    Returns:
        Confirmation message.
    """
    if age:
        character_data["age"] = age
    if height:
        character_data["height"] = height
    if weight:
        character_data["weight"] = weight
    if eyes:
        character_data["eyes"] = eyes
    if skin:
        character_data["skin"] = skin
    if hair:
        character_data["hair"] = hair
    
    return "Physical description updated."


@tool
def set_backstory(backstory: str) -> str:
    """Set the character's backstory.
    
    Args:
        backstory: A short summary of the character's backstory
    
    Returns:
        Confirmation message.
    """
    character_data["backstory"] = backstory
    return "Character backstory set."


@tool
def finalize_character() -> str:
    """Finalize and calculate all derived stats for the character.
    
    This should be called after all basic information is set. It calculates:
    - Final ability scores (with species increases)
    - Ability modifiers
    - Saving throw proficiencies
    - Skill proficiencies
    - Passive Perception/Investigation/Insight
    - AC, HP, Initiative, Speed
    - Equipment
    
    Returns:
        A formatted summary of the finalized character.
    """
    # Apply species ability increases if not already applied
    if character_data["species"] and any(character_data["ability_scores"].values()):
        base_scores = character_data["ability_scores"].copy()
        updated_scores = apply_species_ability_increases(
            base_scores, 
            character_data["species"], 
            character_data["subspecies"]
        )
        character_data["ability_scores"] = updated_scores
        
        # Recalculate modifiers
        for ability, score in updated_scores.items():
            character_data["ability_modifiers"][ability] = calculate_ability_modifier(score)
    
    # Calculate proficiency bonus
    level = character_data["level"]
    proficiency_bonus = get_proficiency_bonus(level)
    
    # Calculate HP
    if character_data["class"] and character_data["ability_modifiers"]["Constitution"] is not None:
        con_mod = character_data["ability_modifiers"]["Constitution"]
        hp, hit_dice = calculate_hit_points(character_data["class"], level, con_mod)
        character_data["hit_points"] = hp
        character_data["hit_dice"] = hit_dice
    
    # Calculate AC (simplified - assumes light armor or unarmored)
    if character_data["ability_modifiers"]["Dexterity"] is not None:
        dex_mod = character_data["ability_modifiers"]["Dexterity"]
        character_data["armor_class"] = calculate_armor_class(dex_mod)
    
    # Calculate Initiative
    if character_data["ability_modifiers"]["Dexterity"] is not None:
        character_data["initiative"] = character_data["ability_modifiers"]["Dexterity"]
    
    # Calculate passive skills
    wis_mod = character_data["ability_modifiers"].get("Wisdom", 0)
    int_mod = character_data["ability_modifiers"].get("Intelligence", 0)
    
    has_perception = "Perception" in character_data["skill_proficiencies"]
    has_investigation = "Investigation" in character_data["skill_proficiencies"]
    has_insight = "Insight" in character_data["skill_proficiencies"]
    
    character_data["passive_perception"] = calculate_passive_skill(wis_mod, proficiency_bonus, has_perception)
    character_data["passive_investigation"] = calculate_passive_skill(int_mod, proficiency_bonus, has_investigation)
    character_data["passive_insight"] = calculate_passive_skill(wis_mod, proficiency_bonus, has_insight)
    
    # Set speed if not set
    if not character_data["speed"]:
        character_data["speed"] = get_species_speed(character_data["species"], character_data["subspecies"])
    
    return "Character finalized! All derived stats have been calculated. Use get_character_sheet to view the complete character."


def _generate_character_sheet() -> str:
    """Generate a complete, formatted character sheet in Markdown format.
    
    This is a helper function that can be called directly (not as a tool).
    
    Returns:
        A formatted character sheet with all character information.
    """
    result = "=" * 60 + "\n"
    result += "D&D 5e CHARACTER SHEET\n"
    result += "=" * 60 + "\n\n"
    
    # Basic Information
    result += "**Character Name:** " + (character_data["name"] or "Not set") + "\n\n"
    
    class_level = ""
    if character_data["class"]:
        class_level = f"{character_data['class']} {character_data['level']}"
    else:
        class_level = "Not set"
    result += f"**Class & Level:** {class_level}\n\n"
    
    species_display = ""
    if character_data["species"]:
        if character_data["subspecies"]:
            species_display = f"{character_data['subspecies']} {character_data['species']}"
        else:
            species_display = character_data["species"]
    else:
        species_display = "Not set"
    result += f"**Species:** {species_display}\n\n"
    
    result += f"**Background:** {character_data['background'] or 'Not set'}\n\n"
    result += f"**Alignment:** {character_data['alignment'] or 'Not set'}\n\n"
    result += f"**Experience Points:** {character_data['experience_points']}\n\n"
    
    # Ability Scores
    scores = character_data["ability_scores"]
    modifiers = character_data["ability_modifiers"]
    
    if any(scores.values()):
        result += "**Ability Scores:**\n"
        abil_str = []
        for ability in ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]:
            score = scores.get(ability)
            mod = modifiers.get(ability)
            if score is not None:
                mod_str = f"+{mod}" if mod >= 0 else str(mod)
                abil_str.append(f"**{ability[:3].upper()}:** {score} ({mod_str})")
        result += " ".join(abil_str) + "\n\n"
    
    # Skills
    if character_data["skill_proficiencies"]:
        result += "**Skills:** " + ", ".join(character_data["skill_proficiencies"]) + "\n\n"
    
    # Combat Stats
    result += "**Combat Stats:**\n"
    if character_data["armor_class"] is not None:
        result += f"  AC: {character_data['armor_class']}\n"
    if character_data["initiative"] is not None:
        init_str = f"+{character_data['initiative']}" if character_data['initiative'] >= 0 else str(character_data['initiative'])
        result += f"  Initiative: {init_str}\n"
    if character_data["speed"]:
        result += f"  Speed: {character_data['speed']} ft\n"
    if character_data["hit_points"]:
        result += f"  HP: {character_data['hit_points']} ({character_data['hit_dice']})\n"
    result += "\n"
    
    # Equipment
    if character_data["equipment"]:
        result += f"**Equipment:** {', '.join(character_data['equipment'])}\n\n"
    
    # Background Details
    if character_data["personality_trait"]:
        result += f"**Trait:** {character_data['personality_trait']}\n\n"
    if character_data["ideal"]:
        result += f"**Ideal:** {character_data['ideal']}\n\n"
    if character_data["bond"]:
        result += f"**Bond:** {character_data['bond']}\n\n"
    if character_data["flaw"]:
        result += f"**Flaw:** {character_data['flaw']}\n\n"
    if character_data["background_feature"]:
        result += f"**Background Feature:** {character_data['background_feature']}\n\n"
    
    # Features
    if character_data["class_features"]:
        result += f"**Features:** {', '.join(character_data['class_features'])}\n\n"
    
    # Languages
    if character_data["language_proficiencies"]:
        result += f"**Languages:** {', '.join(character_data['language_proficiencies'])}\n\n"
    
    # Passive Skills
    if character_data["passive_perception"]:
        result += f"**Passive Perception:** {character_data['passive_perception']}\n"
    if character_data["passive_investigation"]:
        result += f"**Passive Investigation:** {character_data['passive_investigation']}\n"
    if character_data["passive_insight"]:
        result += f"**Passive Insight:** {character_data['passive_insight']}\n"
    
    result += "\n" + "=" * 60 + "\n"
    
    return result


@tool
def get_character_sheet() -> str:
    """Get a complete, formatted character sheet in Markdown format.
    
    Returns:
        A formatted character sheet with all character information.
    """
    return _generate_character_sheet()


@tool
def export_character_json(filename: str = None) -> str:
    """Export the character to a JSON file.
    
    Args:
        filename: Optional filename (default: character_name.json or character.json)
    
    Returns:
        Confirmation message with file path.
    """
    if not filename:
        name = character_data.get("name", "character")
        # Sanitize filename
        filename = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not filename:
            filename = "character"
        filename += ".json"
    
    if not filename.endswith(".json"):
        filename += ".json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(character_data, f, indent=2)
        return f"Character exported to {filename}"
    except Exception as e:
        return f"Error exporting character: {e}"


@tool
def export_character_markdown(filename: str = None) -> str:
    """Export the character to a Markdown file.
    
    Args:
        filename: Optional filename (default: character_name.md or character.md)
    
    Returns:
        Confirmation message with file path.
    """
    if not filename:
        name = character_data.get("name", "character")
        # Sanitize filename
        filename = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not filename:
            filename = "character"
        filename += ".md"
    
    if not filename.endswith(".md"):
        filename += ".md"
    
    try:
        sheet = get_character_sheet()
        with open(filename, 'w') as f:
            f.write(sheet)
        return f"Character exported to {filename}"
    except Exception as e:
        return f"Error exporting character: {e}"


def create_agent() -> AgentExecutor:
    """
    Create and configure the LangChain agent with all character creation tools.
    
    Sets up the OpenAI LLM, defines all available tools, and creates
    the agent executor with a system prompt that guides the character
    creation workflow.
    """
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not found. Please set it in your .env file.")
    
    # Initialize the LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=api_key
    )
    
    # Define all tools
    tools = [
        roll_ability_scores,
        generate_point_buy_scores,
        generate_standard_array_scores,
        set_character_name,
        set_character_class,
        set_character_species,
        set_character_background,
        set_alignment,
        set_background_personality,
        set_physical_description,
        set_backstory,
        finalize_character,
        get_character_sheet,
        export_character_json,
        export_character_markdown
    ]
    
    # Create the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful D&D 5e character creation assistant following Player's Handbook (PHB) rules only.

Your role is to guide users through creating complete, rule-compliant D&D 5e characters.

WORKFLOW:
1. Ask the user for basic information:
   - Character name
   - Class and level (default level 1)
   - Species (race) and subspecies if applicable
   - Background
   - Alignment

2. Ask how they want to determine ability scores:
   - Roll (4d6 drop lowest) - use roll_ability_scores
   - 27 point buy - use generate_point_buy_scores and help allocate points
   - Standard array (15, 14, 13, 12, 10, 8) - use generate_standard_array_scores

3. After ability scores are set, if species is set, the system will automatically apply racial ability score increases.

4. Ask for optional details:
   - Background personality (trait, ideal, bond, flaw) - you can suggest options from the background or allow custom
   - Physical description (age, height, weight, eyes, skin, hair)
   - Backstory

5. Call finalize_character to calculate all derived stats.

6. Display the complete character sheet using get_character_sheet.

7. Offer to export the character (JSON or Markdown).

IMPORTANT RULES:
- Only use PHB classes, backgrounds, and species - no homebrew
- Follow PHB rules exactly for ability scores, proficiencies, and features
- Be friendly and conversational
- Guide users step-by-step through the process
- Always confirm important choices
- After setting key information, show a summary using get_character_sheet

Always use the available tools to perform actions."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    # Create the agent
    agent = create_openai_tools_agent(llm, tools, prompt)
    
    # Create the executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True
    )
    
    return agent_executor


def main():
    """Main interactive loop for character creation."""
    print("=" * 60)
    print("D&D 5e Character Creation Assistant")
    print("=" * 60)
    print("\nI'll help you create a complete D&D 5e character following PHB rules!")
    print("\nI'll guide you through:")
    print("  - Setting basic information (name, class, species, background, alignment)")
    print("  - Generating ability scores (rolling, point buy, or standard array)")
    print("  - Calculating all derived stats")
    print("  - Creating a complete character sheet")
    print("  - Exporting your character (JSON or Markdown)")
    print("\nType 'quit' or 'exit' when finished.\n")
    
    try:
        agent_executor = create_agent()
    except ValueError as e:
        print(f"\nError: {e}")
        print("Please set your OPENAI_API_KEY in a .env file.")
        return
    
    chat_history = []
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n" + "=" * 60)
                print("Final Character Sheet:")
                print("=" * 60)
                sheet = get_character_sheet()
                print(sheet)
                print("Thanks for using the Character Creation Assistant!")
                break
            
            # Run the agent
            response = agent_executor.invoke({
                "input": user_input,
                "chat_history": chat_history
            })
            
            # Display the response
            print(f"\nAssistant: {response['output']}")
            
            # Update chat history
            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=response['output']))
            
        except KeyboardInterrupt:
            print("\n\nInterrupted by user.")
            print("\nFinal Character Sheet:")
            sheet = get_character_sheet()
            print(sheet)
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again or type 'quit' to exit.")


if __name__ == "__main__":
    main()
