import falcon

from falcon_swoop import OpResponseDoc, SwoopResource, operation, path_param, query_param
from falcon_swoop_example.service import (
    Comment,
    ItemCreated,
    ItemNotFoundError,
    ListOfCommentRecords,
    ListOfNoteRecords,
    Note,
    NoteRecord,
    PublicNoteBoardService,
)


class NotesController(SwoopResource):
    def __init__(self, note_board_service: PublicNoteBoardService) -> None:
        super().__init__("/notes")
        self.note_board_service = note_board_service

    @operation(method="GET", summary="List available notes", tags=["note"])
    def list_notes(
        self,
        count: int = query_param(default=100),
        offset: int = query_param(default=0),
        tag: str | None = query_param(default=None),
    ) -> ListOfNoteRecords:
        return self.note_board_service.get_notes(count, offset, tag)

    @operation(method="POST", summary="Add new note", tags=["note"])
    def add_note(self, note: Note) -> ItemCreated:
        return self.note_board_service.add_note(note)


no_note_found_doc = OpResponseDoc("No note found for given id")


class NoteController(SwoopResource):
    def __init__(self, note_board_service: PublicNoteBoardService) -> None:
        super().__init__("/notes/{note_id}")
        self.note_board_service = note_board_service

    @operation(method="GET", summary="Get note for id", tags=["note"], more_response_docs={404: no_note_found_doc})
    def get_note(self, note_id: str = path_param()) -> NoteRecord:
        try:
            return self.note_board_service.get_note(note_id)
        except ItemNotFoundError:
            raise falcon.HTTPNotFound()


class CommentsController(SwoopResource):
    def __init__(self, note_board_service: PublicNoteBoardService) -> None:
        super().__init__("/notes/{note_id}/comments")
        self.note_board_service = note_board_service

    @operation(
        method="GET", summary="List comments for note", tags=["comment"], more_response_docs={404: no_note_found_doc}
    )
    def list_note_comments(self, note_id: str = path_param()) -> ListOfCommentRecords:
        try:
            return self.note_board_service.get_note_comments(note_id)
        except ItemNotFoundError:
            raise falcon.HTTPNotFound()

    @operation(method="POST", summary="Add new comment", tags=["comment"], more_response_docs={404: no_note_found_doc})
    def add_note_comment(self, comment: Comment, note_id: str = path_param()) -> ItemCreated:
        return self.note_board_service.add_comment(note_id, comment)
