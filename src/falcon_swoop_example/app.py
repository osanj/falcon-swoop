import falcon

from falcon_swoop import SwoopApp
from falcon_swoop_example.controller import CommentsController, NoteController, NotesController
from falcon_swoop_example.service import PublicNoteBoardService


def build() -> falcon.App:  # type: ignore
    note_board = PublicNoteBoardService()

    app = falcon.App()
    swoop = SwoopApp(
        app,
        title="Notes App",
        version="1.0.0",
        summary="Public note board that anyone can add notes. Anyone can comment on notes.",
    )
    swoop.add_route(NotesController(note_board))
    swoop.add_route(NoteController(note_board))
    swoop.add_route(CommentsController(note_board))

    return app
