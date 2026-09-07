"""作文题库种子数据(内置 JSON,无需 LLM;契约见 docs/API.md 3.5)。"""

from .database import SessionLocal
from .models import WritingTopic

TOPICS = [
    {"id": "t_1", "title": "My Family", "level": "A1", "stage": "primary",
     "prompt": "Write a short passage about your family. Introduce the people in your family and describe what you like to do together.",
     "keywords": ["family", "introduce", "together"]},
    {"id": "t_2", "title": "My Daily Routine", "level": "A1", "stage": "primary",
     "prompt": "Describe your daily routine. Write about what you do in the morning, in the afternoon, and in the evening.",
     "keywords": ["routine", "morning", "evening"]},
    {"id": "t_3", "title": "My Favorite Food", "level": "A1", "stage": "primary",
     "prompt": "Write about your favorite food. Say what it is, how often you eat it, and why you like it.",
     "keywords": ["food", "like", "why"]},
    {"id": "t_4", "title": "My Best Friend", "level": "A2", "stage": "primary",
     "prompt": "Write a passage about your best friend. Describe what he or she looks like, his or her personality, and what you do together.",
     "keywords": ["friend", "personality", "activities"]},
    {"id": "t_5", "title": "A Memorable Trip", "level": "A2", "stage": "primary",
     "prompt": "Describe a trip you will never forget. Say where you went, who you went with, what you did, and why it was special.",
     "keywords": ["trip", "memory", "experience"]},
    {"id": "t_6", "title": "My Hobbies", "level": "A2", "stage": "primary",
     "prompt": "Write about your hobbies. Explain what you like to do in your free time and why these activities are meaningful to you.",
     "keywords": ["hobby", "free time", "meaningful"]},
    {"id": "t_7", "title": "My Favorite Season", "level": "B1", "stage": "junior",
     "prompt": "Write an essay about your favorite season. Describe the weather, activities, and why you like it.",
     "keywords": ["weather", "activities", "feelings"]},
    {"id": "t_8", "title": "The Importance of Sports", "level": "B1", "stage": "junior",
     "prompt": "Write an essay about why sports are important in our lives. Discuss the physical and mental benefits with examples.",
     "keywords": ["sports", "health", "benefits"]},
    {"id": "t_9", "title": "Online Shopping", "level": "B1", "stage": "junior",
     "prompt": "Write an essay about online shopping. Discuss its advantages and disadvantages, and give your own opinion.",
     "keywords": ["shopping", "advantages", "disadvantages"]},
    {"id": "t_10", "title": "My Dream Job", "level": "B1", "stage": "junior",
     "prompt": "Write an essay about your dream job. Describe what the job is, why you want it, and what you will do to achieve it.",
     "keywords": ["job", "dream", "plan"]},
    {"id": "t_11", "title": "Environmental Protection", "level": "B2", "stage": "senior",
     "prompt": "Write an essay on environmental protection. Analyze the major environmental problems today and suggest what individuals and governments can do.",
     "keywords": ["environment", "problems", "solutions"]},
    {"id": "t_12", "title": "Should Students Use Smartphones in Class?", "level": "B2", "stage": "senior",
     "prompt": "Some schools ban smartphones in class while others encourage their use for learning. Discuss both views and give your own opinion.",
     "keywords": ["smartphones", "education", "opinion"]},
    {"id": "t_13", "title": "The Impact of Social Media", "level": "B2", "stage": "senior",
     "prompt": "Write an essay about the impact of social media on young people. Discuss both positive and negative effects and state your position.",
     "keywords": ["social media", "young people", "impact"]},
    {"id": "t_14", "title": "Globalization and Local Culture", "level": "C1", "stage": "senior",
     "prompt": "Write an essay discussing whether globalization threatens local cultures or enriches them. Develop a well-reasoned argument with evidence.",
     "keywords": ["globalization", "culture", "argument"]},
    {"id": "t_15", "title": "Artificial Intelligence in Our Lives", "level": "C1", "stage": "senior",
     "prompt": "Write an essay analyzing how artificial intelligence is transforming work and daily life. Consider both opportunities and risks, and conclude with your reasoned view.",
     "keywords": ["AI", "transformation", "opportunities and risks"]},
]

# CEFR 等级 → 学段(用于老库回填)
LEVEL_TO_STAGE = {"A1": "primary", "A2": "primary", "B1": "junior", "B2": "senior", "C1": "senior"}


def seed_topics():
    db = SessionLocal()
    try:
        # 按固定 id 逐个补插(兼容老库与部分删除场景)。
        # 不能只按「表是否为空」判断:用户删除部分内置题后永远不会恢复,
        # 而全删光反而会恢复,同一功能两种行为。
        for topic in TOPICS:
            if not db.get(WritingTopic, topic["id"]):
                db.add(WritingTopic(**topic))
        # 老库回填:按 CEFR 等级补学段字段(升级学段分类后自动迁移)
        updated = False
        for t in db.query(WritingTopic).all():
            if not t.stage:
                t.stage = LEVEL_TO_STAGE.get(t.level, "")
                updated = True
        if updated:
            print(f"[seed] 已为 {db.query(WritingTopic).count()} 道旧题目回填学段字段")
        db.commit()
    finally:
        db.close()
