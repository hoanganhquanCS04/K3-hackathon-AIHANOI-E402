"""
Transcript Ingestion Script v4 - NEW SCHEMA

Schema moi phu hop voi cau truc transcript:
- Lecture -> Section -> Turn (hierarchical)
- Section COVERS Concept
- Lecture INTRODUCES Concept  
- Concept RELATED_TO Concept

Cau truc:
- Lecture: bai giang (tu header)
- Section: phan trong bai (## Heading)
- Turn: cau hoi/tra loi ([Txx-NNN])
- Concept: khai niem (trich xuat tu LLM)
- Question: cau hoi noi bat
- Reference: tai lieu tham khao

Relationships:
- Turn ->[:BELONGS_TO]-> Section
- Section ->[:BELONGS_TO]-> Lecture
- Section ->[:COVERS]-> Concept
- Lecture ->[:INTRODUCES]-> Concept
- Concept ->[:RELATED_TO]-> Concept

How to use:
1. Ensure .env is configured with Neo4j credentials
2. Run: python scripts/ingest_transcripts.py
"""

from __future__ import annotations

import re
import sys
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from neo4j import GraphDatabase
from dotenv import load_dotenv
import openai

load_dotenv()


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Turn:
    id: str           # T01-001
    speaker: str       # tutor | student | activity
    speaker_label: Optional[str]  # "học viên" or None
    content: str
    is_activity: bool = False
    is_illegible: bool = False
    is_question: bool = False


@dataclass
class Section:
    id: str
    title: str
    section_index: int
    turns: list[Turn] = field(default_factory=list)


@dataclass
class Lecture:
    id: str
    title: str
    day: str
    source_file: str
    sections: list[Section] = field(default_factory=list)
    
    @property
    def turn_count(self) -> int:
        return sum(len(s.turns) for s in self.sections)


@dataclass
class ExtractedMetadata:
    topics: list[str]
    concepts: list[str]
    questions: list[str]
    references: list[dict]


# =============================================================================
# TRANSCRIPT PARSING
# =============================================================================

class TranscriptParser:
    """Parse transcript markdown theo quy uoc VLearn"""
    
    def parse(self, file_path: str) -> Lecture:
        """Parse transcript markdown file"""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        
        # Parse header (first 6 lines)
        lecture = self._parse_header(lines)
        
        # Parse sections and turns
        lecture.sections = self._parse_body(lines, lecture.id)
        
        return lecture
    
    def _parse_header(self, lines: list[str]) -> Lecture:
        """Parse header: title, day, source"""
        
        # Line 1: # Transcript bài giảng (bản sạch) — Day 2 (sáng) — Xác định bài toán kinh doanh cho AI
        title_match = re.search(r'— (.+)$', lines[0])
        title = title_match.group(1).strip() if title_match else "Unknown"
        
        # Line 3: > **Nguồn:** `transcript_2/01.md` · **Định vị buổi:** Day 2 (sáng)
        source_match = re.search(r'`([^`]+)`', lines[2])
        source_file = source_match.group(1) if source_match else ""
        
        day_match = re.search(r'Day[:\s]+(\d+)', lines[2])
        day = f"Day {day_match.group(1)}" if day_match else "Unknown"
        
        # Line 4-5: có thể có buổi sáng/chieu
        if 'sáng' in lines[2] or 'chiều' in lines[2]:
            period_match = re.search(r'(sáng|chiều)', lines[2])
            if period_match:
                day = f"Day {day_match.group(1)} ({period_match.group(1)})" if day_match else f"Day X ({period_match.group(1)})"
        
        # Generate lecture_id from filename
        lecture_id = Path(source_file).stem.replace('transcript_', 'transcript_')
        if not lecture_id:
            lecture_id = Path(file_path).stem
        
        return Lecture(
            id=lecture_id,
            title=title,
            day=day,
            source_file=source_file,
            sections=[]
        )
    
    def _parse_body(self, lines: list[str], lecture_id: str) -> list[Section]:
        """Parse body: extract sections and turns"""
        
        sections = []
        current_section = None
        current_section_turns = []
        current_section_idx = 0
        turn_index = 0
        
        for i, line in enumerate(lines[6:], start=6):  # Skip header (6 lines)
            stripped = line.strip()
            
            # Section header: ## Heading
            if stripped.startswith('## '):
                # Save previous section
                if current_section and current_section_turns:
                    sections.append(Section(
                        id=f"section_{current_section_idx:02d}",
                        title=current_section,
                        section_index=current_section_idx,
                        turns=current_section_turns
                    ))
                
                # Start new section
                current_section = stripped[3:].strip()
                current_section_idx += 1
                current_section_turns = []
            
            # Turn: **[Txx-NNN]** content
            elif stripped.startswith('**[') and ']**' in stripped:
                turn = self._parse_turn(stripped, lecture_id)
                if turn:
                    current_section_turns.append(turn)
                    turn_index += 1
            
            # Skip metadata lines and empty lines
            elif stripped.startswith('>') or not stripped:
                continue
        
        # Save last section
        if current_section and current_section_turns:
            sections.append(Section(
                id=f"section_{current_section_idx:02d}",
                title=current_section,
                section_index=current_section_idx,
                turns=current_section_turns
            ))
        
        return sections
    
    def _parse_turn(self, line: str, lecture_id: str) -> Optional[Turn]:
        """Parse a single turn line"""
        
        # Extract turn ID: **[T01-001]**
        id_match = re.search(r'\[(T\d{2}-\d{3})\]', line)
        if not id_match:
            return None
        
        turn_id = id_match.group(1)
        
        # Extract content (after ** and before any markdown)
        content_match = re.search(r'\]\*\*\s*(.+?)(?:\s*\[|$)', line, re.DOTALL)
        content = content_match.group(1).strip() if content_match else ""
        
        if not content:
            return None
        
        # Check for activity
        if '[Hoạt động lớp:' in content:
            return Turn(
                id=turn_id,
                speaker="activity",
                speaker_label=None,
                content=content,
                is_activity=True
            )
        
        # Check for student input
        if '[học viên]:' in content or '[Học viên]:' in content:
            is_question = '?' in content
            return Turn(
                id=turn_id,
                speaker="student",
                speaker_label="học viên",
                content=content,
                is_question=is_question
            )
        
        # Check for illegible
        if '[không nghe rõ]' in content:
            return Turn(
                id=turn_id,
                speaker="tutor",
                speaker_label=None,
                content=content,
                is_illegible=True
            )
        
        # Default: tutor
        return Turn(
            id=turn_id,
            speaker="tutor",
            speaker_label=None,
            content=content
        )


# =============================================================================
# METADATA EXTRACTION (LLM)
# =============================================================================

def extract_metadata_llm(lecture: Lecture) -> ExtractedMetadata:
    """Use LLM to extract topics, concepts, questions, references"""
    
    # Combine all content for context
    all_content = f"# {lecture.title}\n\n"
    for section in lecture.sections:
        all_content += f"## {section.title}\n\n"
        for turn in section.turns:
            all_content += f"[{turn.id}]: {turn.content}\n\n"
    
    prompt = f"""
Bạn là chuyên gia AI. Trích xuất thông tin từ transcript bài giảng:

{all_content[:10000]}

Trả về JSON với cấu trúc:
{{
    "topics": ["topic1", "topic2", ...],  // 5-10 chủ đề chính
    "concepts": ["concept1", "concept2", ...],  // 5-10 khái niệm quan trọng
    "questions": ["câu hỏi 1?", "câu hỏi 2?", ...],  // 3-5 câu hỏi nổi bật
    "references": [{{"title": "...", "author": "...", "type": "book"}}]  // Sách/bài viết được đề cập
}}
"""
    
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    data = json.loads(response.choices[0].message.content)
    
    return ExtractedMetadata(
        topics=data.get("topics", []),
        concepts=data.get("concepts", []),
        questions=data.get("questions", []),
        references=data.get("references", [])
    )


# =============================================================================
# NEO4J OPERATIONS
# =============================================================================

def get_neo4j_driver():
    """Create Neo4j driver from environment variables."""
    import os
    
    uri = os.getenv('NEO4J_URI', 'neo4j+s://localhost:7687')
    username = os.getenv('NEO4J_USERNAME', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', '')
    database = os.getenv('NEO4J_DATABASE', 'neo4j')
    
    driver = GraphDatabase.driver(uri, auth=(username, password))
    return driver, database


def drop_all_data(driver, database: str):
    """Drop ALL existing data in the database."""
    print("=" * 60)
    print("DROPPING ALL EXISTING DATA...")
    print("=" * 60)
    
    with driver.session(database=database) as session:
        # Delete all nodes and relationships
        session.run("MATCH (n) DETACH DELETE n")
        
        # Also drop constraints and indexes (optional, will recreate)
        # Note: In Neo4j Aura, constraints cannot be dropped easily
    
    print("All data dropped successfully!")
    print()


def create_schema(driver, database: str):
    """Create constraints and indexes for the new schema."""
    print("Creating schema constraints and indexes...")
    
    # New schema constraints (with Section instead of Topic)
    constraints = [
        "CREATE CONSTRAINT lecture_id IF NOT EXISTS FOR (n:Lecture) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT section_id IF NOT EXISTS FOR (n:Section) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT turn_id IF NOT EXISTS FOR (n:Turn) REQUIRE n.id IS UNIQUE",
        "CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (n:Concept) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT question_text IF NOT EXISTS FOR (n:Question) REQUIRE n.text IS UNIQUE",
    ]

    indexes = [
        "CREATE INDEX lecture_title IF NOT EXISTS FOR (n:Lecture) ON (n.title)",
        "CREATE INDEX lecture_day IF NOT EXISTS FOR (n:Lecture) ON (n.day)",
        "CREATE INDEX section_title IF NOT EXISTS FOR (n:Section) ON (n.title)",
        "CREATE INDEX section_idx IF NOT EXISTS FOR (n:Section) ON (n.section_index)",
        "CREATE INDEX turn_speaker IF NOT EXISTS FOR (n:Turn) ON (n.speaker)",
        "CREATE INDEX concept_freq IF NOT EXISTS FOR (n:Concept) ON (n.frequency)",
    ]

    with driver.session(database=database) as session:
        for c in constraints:
            try:
                session.run(c)
                print(f"  Created constraint: {c.split('FOR (n:')[1].split(')')[0]}")
            except Exception as e:
                # Constraint might already exist
                pass
        
        for i in indexes:
            try:
                session.run(i)
                print(f"  Created index: {i.split('INDEX')[1].split('IF')[0].strip()}")
            except Exception as e:
                # Index might already exist
                pass
    
    print("Schema created!")
    print()


def ingest_lecture(driver, database: str, lecture: Lecture, metadata: ExtractedMetadata) -> dict:
    """Ingest a single lecture into Neo4j following new schema."""
    
    stats = {
        'sections': 0,
        'turns': 0,
        'concepts': 0,
        'questions': 0,
        'references': 0,
    }
    
    with driver.session(database=database) as session:
        
        # === 1. Create Lecture node ===
        session.run("""
            MERGE (l:Lecture {id: $id})
            SET l.title = $title,
                l.day = $day,
                l.source_file = $source,
                l.section_count = $section_count,
                l.turn_count = $turn_count
        """, {
            "id": lecture.id,
            "title": lecture.title,
            "day": lecture.day,
            "source": lecture.source_file,
            "section_count": len(lecture.sections),
            "turn_count": lecture.turn_count
        })
        
        # === 2. Create Section nodes and relationships ===
        for section in lecture.sections:
            session.run("""
                MERGE (s:Section {id: $id})
                SET s.title = $title,
                    s.section_index = $idx,
                    s.lecture_id = $lecture_id,
                    s.turn_count = $turn_count,
                    s.has_student_input = $has_student
            """, {
                "id": section.id,
                "title": section.title,
                "idx": section.section_index,
                "lecture_id": lecture.id,
                "turn_count": len(section.turns),
                "has_student": any(t.speaker == "student" for t in section.turns)
            })
            stats['sections'] += 1
            
            # BELONGS_TO: Section -> Lecture
            session.run("""
                MATCH (s:Section {id: $section_id})
                MATCH (l:Lecture {id: $lecture_id})
                MERGE (s)-[:BELONGS_TO]->(l)
            """, {"section_id": section.id, "lecture_id": lecture.id})
            
            # === 3. Create Turn nodes and relationships ===
            for turn in section.turns:
                session.run("""
                    MERGE (t:Turn {id: $id})
                    SET t.content = $content,
                        t.speaker = $speaker,
                        t.speaker_label = $label,
                        t.is_activity = $is_activity,
                        t.is_illegible = $is_illegible,
                        t.is_question = $is_question,
                        t.section_id = $section_id,
                        t.lecture_id = $lecture_id,
                        t.turn_index = $turn_idx
                """, {
                    "id": turn.id,
                    "content": turn.content[:2000],  # Truncate for Neo4j
                    "speaker": turn.speaker,
                    "label": turn.speaker_label,
                    "is_activity": turn.is_activity,
                    "is_illegible": turn.is_illegible,
                    "is_question": turn.is_question,
                    "section_id": section.id,
                    "lecture_id": lecture.id,
                    "turn_idx": int(turn.id.split('-')[1])
                })
                stats['turns'] += 1
                
                # BELONGS_TO: Turn -> Section
                session.run("""
                    MATCH (t:Turn {id: $turn_id})
                    MATCH (s:Section {id: $section_id})
                    MERGE (t)-[:BELONGS_TO]->(s)
                """, {"turn_id": turn.id, "section_id": section.id})
        
        # === 4. Create Concept nodes ===
        for concept_name in metadata.concepts:
            session.run("""
                MERGE (c:Concept {name: $name})
                SET c.frequency = coalesce(c.frequency, 0) + 1,
                    c.updated_at = datetime()
            """, {"name": concept_name})
            stats['concepts'] += 1
        
        # === 5. Create Question nodes ===
        for question_text in metadata.questions:
            session.run("""
                MERGE (q:Question {text: $text})
                SET q.type = 'conceptual',
                    q.lecture_id = $lecture_id
            """, {"text": question_text, "lecture_id": lecture.id})
            stats['questions'] += 1
        
        # === 6. Create Reference nodes ===
        for ref in metadata.references:
            session.run("""
                MERGE (r:Reference {title: $title})
                SET r.author = $author,
                    r.type = $type
            """, {
                "title": ref.get("title", ""),
                "author": ref.get("author", ""),
                "type": ref.get("type", "other")
            })
            stats['references'] += 1
        
        # === 7. Create relationships ===
        
        # COVERS: Section -> Concept
        for section in lecture.sections:
            for concept_name in metadata.concepts[:5]:  # First 5 concepts per section
                session.run("""
                    MATCH (s:Section {id: $section_id})
                    MATCH (c:Concept {name: $concept_name})
                    MERGE (s)-[:COVERS]->(c)
                """, {"section_id": section.id, "concept_name": concept_name})
        
        # INTRODUCES: Lecture -> Concept
        for concept_name in metadata.concepts:
            session.run("""
                MATCH (l:Lecture {id: $lecture_id})
                MATCH (c:Concept {name: $concept_name})
                MERGE (l)-[:INTRODUCES]->(c)
            """, {"lecture_id": lecture.id, "concept_name": concept_name})
        
        # RELATED_TO: Concept -> Concept (based on co-occurrence)
        for i, concept1 in enumerate(metadata.concepts[:5]):
            for concept2 in metadata.concepts[i+1:5]:
                session.run("""
                    MATCH (c1:Concept {name: $name1})
                    MATCH (c2:Concept {name: $name2})
                    MERGE (c1)-[:RELATED_TO {type: 'co_occurrence'}]->(c2)
                """, {"name1": concept1, "name2": concept2})
    
    return stats


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 60)
    print("Transcript Ingestion v4 - NEW SCHEMA")
    print("=" * 60)
    print()
    print("Schema moi:")
    print("  - Lecture -> Section -> Turn (hierarchical)")
    print("  - Section COVERS Concept")
    print("  - Lecture INTRODUCES Concept")
    print("  - Concept RELATED_TO Concept")
    print()
    
    driver, database = get_neo4j_driver()
    parser = TranscriptParser()
    
    try:
        driver.verify_connectivity()
        print(f"Connected to Neo4j AuraDB!\n")
        
        # Drop ALL existing data first
        drop_all_data(driver, database)
        
        # Recreate schema
        create_schema(driver, database)
        
        # Find transcript files
        transcript_dir = Path(__file__).parent.parent / 'data' / 'vlearn-pack' / 'transcript'
        
        if not transcript_dir.exists():
            print(f"Transcript directory not found: {transcript_dir}")
            return
        
        transcript_files = sorted(transcript_dir.glob('*-clean.md'))
        
        if not transcript_files:
            print(f"No transcript files found")
            return
        
        print(f"Found {len(transcript_files)} transcript files\n")
        
        # Process each transcript
        total_stats = {
            'lectures': 0,
            'sections': 0,
            'turns': 0,
            'concepts': 0,
            'questions': 0,
            'references': 0,
        }
        
        for transcript_file in transcript_files:
            print(f"Processing: {transcript_file.name}...")
            
            # Parse transcript
            lecture = parser.parse(str(transcript_file))
            print(f"  Title: {lecture.title}")
            print(f"  Day: {lecture.day}")
            print(f"  Sections: {len(lecture.sections)}")
            print(f"  Turns: {lecture.turn_count}")
            
            # Extract metadata with LLM
            print(f"  Extracting metadata with LLM...")
            metadata = extract_metadata_llm(lecture)
            print(f"  Concepts: {len(metadata.concepts)}")
            print(f"  Questions: {len(metadata.questions)}")
            print(f"  References: {len(metadata.references)}")
            
            # Ingest to Neo4j
            stats = ingest_lecture(driver, database, lecture, metadata)
            
            print(f"  [OK] Sections: {stats['sections']}")
            print(f"  [OK] Turns: {stats['turns']}")
            print(f"  [OK] Concepts: {stats['concepts']}")
            print(f"  [OK] Questions: {stats['questions']}")
            print(f"  [OK] References: {stats['references']}")
            print()
            
            total_stats['lectures'] += 1
            for key in total_stats:
                if key != 'lectures':
                    total_stats[key] += stats.get(key, 0)
        
        # Verify final data
        print("=" * 60)
        print("VERIFICATION")
        print("=" * 60)
        
        with driver.session(database=database) as session:
            for node_type in ['Lecture', 'Section', 'Turn', 'Concept', 'Question', 'Reference']:
                result = session.run(f"MATCH (n:{node_type}) RETURN count(n) as count")
                count = result.single()["count"]
                print(f"  {node_type}: {count}")
            
            print("\n  Relationships:")
            result = session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count")
            for record in result:
                print(f"    {record['rel_type']}: {record['count']}")
        
        print("\n" + "=" * 60)
        print("INGESTION COMPLETE!")
        print("=" * 60)
        print(f"\nTotal imported:")
        for key, value in total_stats.items():
            print(f"  - {key.capitalize()}: {value}")
        
        print("\nNew Graph structure:")
        print("  - (Section)-[:BELONGS_TO]->(Lecture)")
        print("  - (Turn)-[:BELONGS_TO]->(Section)")
        print("  - (Section)-[:COVERS]->(Concept)")
        print("  - (Lecture)-[:INTRODUCES]->(Concept)")
        print("  - (Concept)-[:RELATED_TO]->(Concept)")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.close()


if __name__ == '__main__':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    main()
