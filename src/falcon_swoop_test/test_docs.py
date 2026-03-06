from typing import Any

import griffe  # type: ignore[import-untyped]
import pytest

from falcon_swoop import operation, operation_doc
from falcon_swoop.operation import OperationDocKwArgs, OperationKwArgs


def parse_parameters_from_operation_doc_string(
    op: Any, style: griffe.DocstringStyle = "sphinx"
) -> griffe.DocstringSectionParameters:
    doc_string = griffe.Docstring(op.__doc__)
    sections = doc_string.parse(style)
    for section in sections:
        if isinstance(section, griffe.DocstringSectionParameters):
            return section
    raise ValueError("Couldn't find section for parameters among doc string")


def test_decorator_parameter_docs_are_in_sync() -> None:
    operation_params = parse_parameters_from_operation_doc_string(operation)
    operation_doc_params = parse_parameters_from_operation_doc_string(operation_doc)

    shared_param_names = {p.name for p in operation_params.value} & {p.name for p in operation_doc_params.value}
    descriptions_1 = {p.name: p.description for p in operation_params.value if p.name in shared_param_names}
    descriptions_2 = {p.name: p.description for p in operation_doc_params.value if p.name in shared_param_names}
    assert descriptions_1 == descriptions_2


@pytest.mark.parametrize(
    "func,kw_typed_dict,ignore",
    [
        (operation, OperationKwArgs, ("method",)),
        (operation_doc, OperationDocKwArgs, ()),
    ],
)
def test_all_params_documented(
    func: Any,
    kw_typed_dict: type[OperationKwArgs] | type[OperationDocKwArgs],
    ignore: tuple[str],
) -> None:
    params = parse_parameters_from_operation_doc_string(func)
    param_names = {p.name for p in params.value} - set(ignore)
    exp_param_names = set(kw_typed_dict.__annotations__.keys())
    assert param_names == exp_param_names
