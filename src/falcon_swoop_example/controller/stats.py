from datetime import UTC, datetime
from logging import Logger

import falcon
from pydantic import BaseModel

from falcon_swoop import OpBinary, OpContext, OpOutput, SwoopResource, operation, operation_doc
from falcon_swoop_example.controller.admin import ADMIN_SECRET_HDR, DOC_UNAUTHORIZED, AdminSecretVerification
from falcon_swoop_example.service import PublicNoteBoardService


class StatsParameters(BaseModel):
    after: datetime | None = None
    before: datetime | None = None


class TagStatsController(SwoopResource):
    def __init__(
        self, note_board_service: PublicNoteBoardService, admin_verif: AdminSecretVerification, logger: Logger
    ) -> None:
        super().__init__("/api/stats/tags")
        self.note_board_service = note_board_service
        self.admin_verif = admin_verif
        self.logger = logger

    @operation(
        method="GET",
        summary="Get statistics on how often a tag is used",
        tags=["admin"],
        response_content_type="text/csv",
        response_example="news;105\ntechnology;81\nsports;47",
        more_response_docs={401: DOC_UNAUTHORIZED},
    )
    def get_note_count_by_tag(
        self,
        parameters: StatsParameters,
        context: OpContext,
        admin_secret: str | None = ADMIN_SECRET_HDR,
    ) -> OpOutput[OpBinary]:
        self.admin_verif.verify(admin_secret)

        # usage of the context class here is purely performative to show how the raw falcon data can be accessed
        user_agent = context.req.headers.get("user-agent")
        self.logger.info(f"{self.api_route.plain} accessed at={datetime.now(UTC).isoformat()} user-agent={user_agent}")

        counts_by_tag: dict[str, int] = {}
        if parameters.after is None and parameters.before is None:
            for tag, note_ids in self.note_board_service.note_ids_by_tags.items():
                counts_by_tag[tag] = len(note_ids)
        else:
            for tag, note_ids in self.note_board_service.note_ids_by_tags.items():
                note_ids_in_time = []
                for note_id in note_ids:
                    record = self.note_board_service.get_note(note_id)
                    if parameters.before is not None and record.ts_created > parameters.before:
                        continue
                    if parameters.after is not None and record.ts_created < parameters.after:
                        continue
                    note_ids_in_time.append(note_id)
                counts_by_tag[tag] = len(note_ids_in_time)

        csv_lines = []
        for tag, count in counts_by_tag.items():
            csv_lines.append(f"{tag};{count}")
        csv_string = "\n".join(csv_lines)
        return OpOutput(
            payload=OpBinary(csv_string, content_type="text/csv"),
            status_code=200 if len(counts_by_tag) > 0 else 404,
            cache_control="no-store, no-cache, must-revalidate",
        )

    @operation_doc(operation_id="getTags", tags=["admin"], deprecated=True)
    def on_patch(self, req: falcon.Request, resp: falcon.Response) -> None:
        # usage of operation_doc here is purely performative to show how old endpoints may be included in the spec
        resp.text = ",".join(self.note_board_service.note_ids_by_tags.keys())
        resp.status_code = 200
