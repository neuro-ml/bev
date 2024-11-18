# we will try to support both versions 1 and 2 of pydantic while they are more or less popular
try:
    from pydantic import BaseModel, field_validator as _field_validator, model_validator
    from pydantic_core import core_schema


    def field_validator(*args, always=None, **kwargs):
        # we just ignore `always`
        return _field_validator(*args, **kwargs)


    def model_validate(cls, data):
        return cls.model_validate(data)


    def model_dump(obj, **kwargs):
        return obj.model_dump(**kwargs)


    def model_copy(cls, **kwargs):
        return cls.model_copy(**kwargs)


    class NoExtra(BaseModel):
        model_config = {
            'extra': 'forbid'
        }

except ImportError:
    from pydantic import BaseModel, root_validator, validator as _field_validator

    # we don't use this with pydantic==1 anyway
    core_schema = None


    def model_validator(mode: str):
        assert mode == 'before'
        return root_validator(pre=True)


    def field_validator(*args, mode: str = 'after', **kwargs):
        # we just ignore `always`
        assert mode in ('before', 'after')
        if mode == 'before':
            kwargs['pre'] = True
        return _field_validator(*args, **kwargs)


    def model_validate(cls, data):
        return cls.parse_obj(data)


    def model_dump(obj, **kwargs):
        return obj.dict(**kwargs)


    def model_copy(cls, **kwargs):
        return cls.copy(**kwargs)


    class NoExtra(BaseModel):
        class Config:
            extra = 'forbid'
