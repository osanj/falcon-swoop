import logging
from logging import basicConfig, getLogger

import falcon

from falcon_swoop import SwoopApp
from falcon_swoop_example.controller.admin import AdminSecretVerification
from falcon_swoop_example.controller.notes import CommentsController, NoteController, NotesController
from falcon_swoop_example.controller.stats import TagStatsController
from falcon_swoop_example.service import PublicNoteBoardService

logger = getLogger("app")


def build(port: int) -> falcon.App:  # type: ignore
    basicConfig(level=logging.INFO)

    note_board = PublicNoteBoardService()
    admin_verif = AdminSecretVerification("super-secret")

    app = falcon.App()
    swoop = SwoopApp(
        app,
        title="Notes App",
        version="1.0.0",
        summary="Public note board. Anyone can add notes and comment on notes.",
    )
    swoop.add_route(NotesController(note_board))
    swoop.add_route(NoteController(note_board, admin_verif))
    swoop.add_route(CommentsController(note_board))
    swoop.add_route(TagStatsController(note_board, admin_verif, logger))

    logger.info(f"OpenAPI spec at http://localhost:{port}{swoop.spec_json_route}")
    logger.info(f"OpenAPI swagger at http://localhost:{port}{swoop.spec_swagger_route}")

    return app
