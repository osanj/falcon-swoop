import collections
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


class Note(BaseModel):
    author: str = Field(min_length=3)
    message: str = Field(min_length=20)
    tags: list[str]


class NoteRecord(BaseModel):
    note_id: str
    note: Note
    ts_created: datetime


class ListOfNoteRecords(BaseModel):
    records: list[NoteRecord]
    overall_count: int


class Comment(BaseModel):
    author: str = Field(min_length=3)
    message: str = Field(min_length=20)


class CommentRecord(BaseModel):
    note_id: str
    comment_id: str
    comment: Comment
    ts_created: datetime


class ListOfCommentRecords(BaseModel):
    note_id: str
    records: list[CommentRecord]


class ItemCreated(BaseModel):
    id: str


class ItemNotFoundError(ValueError):
    pass


class PublicNoteBoardService:
    def __init__(self) -> None:
        self.note_ids: list[str] = []
        self.note_ids_by_tags: dict[str, list[str]] = collections.defaultdict(list)
        self.notes_by_id: dict[str, NoteRecord] = dict()
        self.comments_by_note_id: dict[str, list[CommentRecord]] = collections.defaultdict(list)

    def add_note(self, note: Note) -> ItemCreated:
        note_id = uuid.uuid4().hex
        note_record = NoteRecord(
            note_id=note_id,
            note=note,
            ts_created=datetime.now(UTC),
        )
        self.note_ids.append(note_id)
        self.notes_by_id[note_id] = note_record
        return ItemCreated(id=note_id)

    def get_note(self, note_id: str) -> NoteRecord:
        record = self.notes_by_id.get(note_id)
        if record is None:
            raise ItemNotFoundError()
        return record

    def get_notes(self, count: int, offset: int, tag: str | None) -> ListOfNoteRecords:
        if tag is None:
            note_ids = self.note_ids[offset : offset + count]
            overall_count = len(note_ids)
        else:
            note_ids = self.note_ids_by_tags[tag][offset : offset + count]
            overall_count = len(self.note_ids_by_tags[tag])
        return ListOfNoteRecords(
            records=[self.notes_by_id[note_id] for note_id in note_ids],
            overall_count=overall_count,
        )

    def add_comment(self, note_id: str, comment: Comment) -> ItemCreated:
        self.get_note(note_id)
        comment_id = uuid.uuid4().hex
        comment_record = CommentRecord(
            note_id=note_id,
            comment_id=comment_id,
            comment=comment,
            ts_created=datetime.now(UTC),
        )
        self.comments_by_note_id[note_id].append(comment_record)
        return ItemCreated(id=comment_id)

    def get_note_comments(self, note_id: str) -> ListOfCommentRecords:
        note = self.get_note(note_id)
        comments = self.comments_by_note_id.get(note.note_id, [])
        return ListOfCommentRecords(note_id=note_id, records=comments)
