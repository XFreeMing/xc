# 虚词大战

一个基于 Streamlit + SQLite 的虚词教学管理系统，帮助教师管理虚词用法、例句，生成试卷并导出为 Word 文档。

## 功能特性

- **虚词用法管理**：CRUD 操作管理虚词用法（EmptyWordAction）
- **例句管理**：支持单个和批量添加例句，自动识别句子中的虚词
- **试卷生成**：根据条件筛选生成试卷，自定义题目数量
- **Word 导出**：导出试卷到 Word 文档，可控制显示选项、答案和高亮

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动应用

```bash
./run.sh
```

或手动启动：

```bash
# 初始化数据库并导入数据
python3 database.py

# 启动 Streamlit 应用
streamlit run app.py
```

应用将在浏览器中打开：`http://localhost:8501`

## 使用说明

### 1. 数据管理

- 查看所有虚词用法
- 筛选特定虚词
- 添加、编辑、删除虚词用法

### 2. 例句管理

- **例句列表**：查看所有例句，支持筛选
- **批量添加**：输入多行例句，系统自动识别虚词并绑定用法
- **手动添加**：为单句选择虚词和用法

### 3. 试卷生成

- 选择虚词和词性筛选条件
- 设置题目数量
- 输入试卷标题
- 生成试卷

### 4. 试卷列表

- 查看所有试卷
- 查看试卷详情
- 导出 Word 文档
  - 控制显示选项（默认隐藏）
  - 控制显示答案（默认隐藏）
  - 控制高亮虚词（默认不高亮）

## 数据结构设计

```python

# 词性
enum class PartOfSpeech:
    VERB = "动词"
    NOUN = "名词"
    ADJECTIVE = "形容词"
    ADVERB = "副词"
    PREPOSITION = "介词"
    CONJUNCTION = "连词"
    PRONOUN = "代词"
    ARTICLE = "冠词"
    PREPOSITION = "介词"
    CONJUNCTION = "连词"
    PRONOUN = "代词"
# 虚词
enum class EmptyWord:
    而 = 1
    何 = 2
    乎 = 3
    乃 = 4
    其 = 5
    且 = 6
    若 = 7
    所 = 8
    为 = 9
    焉 = 10
    也 = 11
    以 = 12
    因 = 13
    于 = 14
    与 = 15
    则 = 16
    者 = 17
    之 = 18

# 底层数据基础管理
# 虚词作用
class EmptyWordAction:
    id: int
    emptyWord: EmptyWord
    partOfSpeech: PartOfSpeech
    action: str
    translation: str

class Sentence:
    id:str
    no:list[int]
    tags: list[str]


# 例句
class ExampleSentence:
    sentence_id: str # 例句ID
    emptyWord: List[EmptyWordAction] # 虚词作用

# 题目
class Question:
    id: int
    emptyWordAction: EmptyWordAction
    exampleSentence: ExampleSentence
    options: list[EmptyWordAction]

# 卷子
class Paper:
    id: int
    title: str
    question_count: int
    questions: list[Question]
    create_time: datetime



# 交互类

class Student:
    id: str # 手机号
    nick_name: str # 昵称
    avatar: str # 头像
    gender: int # 性别



# 答题记录
class Answer:
    id: int
    student: int
    question: int
    answer: EmptyWordAction
    answer_time: int
    is_correct: bool
    create_time: datetime



```
