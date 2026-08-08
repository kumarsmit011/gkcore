from pydantic import BaseModel, ValidationInfo, field_validator, model_validator
from typing import Optional
from typing_extensions import Self

from gkcore.views.group_subgroup.services import (
    check_duplicate_group_name,
    check_groupcode_exists,
    check_parent_group_exists,
)


class GroupSubgroup(BaseModel):
    groupname: str
    subgroupof: int

    @field_validator("subgroupof")
    @classmethod
    def subgroupof_validate(cls, value: int, info: ValidationInfo) -> int:
        check_parent_group_exists(
             value,
             info.context["orgcode"],
        )
        return value

    @model_validator(mode="after")
    def validate(self, info: ValidationInfo) -> Self:
        check_duplicate_group_name(
             self.groupname,
             info.context["orgcode"],
             getattr(self, "custid", None),
        )
        return self


class GroupSubgroupUpdate(GroupSubgroup):
    groupcode: int

    @field_validator("groupcode")
    @classmethod
    def groupcode_validate(cls, value: int, info: ValidationInfo) -> int:
        check_groupcode_exists(
             value,
             info.context["orgcode"],
        )
        return value
