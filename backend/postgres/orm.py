from datetime import datetime
from typing import Any, Optional, Dict, Literal

from backend.postgres import ORMBase
from sqlalchemy import Text, JSON, ForeignKey, Integer, DateTime, Float, ARRAY, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column, relationship


class APIRequests(ORMBase):
    """
    Persistence of API interaction.

    Attributes:
        codeversion: version of the current code implementation in date format
        model: model used to query ex. gpt-3.5-turbo (string)
        output: the actual output of the model
        notes: a description of what was being tested/performed
        request: the request object sent to the api endpoint (json)
        shots: the number of shots (> 0 if few shots learning)
        status: success, fail, too long etc. (string)
        response: model response
        about: what things we inquired about (ex. paper id, table id etc.) (json)
        request_tokens: number of tokens used for request
        response_tokens: number of tokens used for response
    """

    __tablename__ = "llm_api_request"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_added: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    codeversion: Mapped[str] = mapped_column(VARCHAR(length=15))
    model: Mapped[str] = mapped_column(Text)
    output: Mapped[str] = mapped_column(Text)
    status: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    request: Mapped[Dict] = mapped_column(JSON)
    shots: Mapped[int] = mapped_column(Integer, default=0)
    response: Mapped[Dict] = mapped_column(JSON)
    about: Mapped[Dict] = mapped_column(JSON)
    request_tokens: Mapped[int] = mapped_column(Integer, default=0)
    response_tokens: Mapped[int] = mapped_column(Integer, default=0)

    def __init__(self, **kw: Any):
        super().__init__(**kw)
        if self.date_added is None:
            self.date_added = datetime.now()


FILEFORMAT = Literal["xml", "html", "pdf", "txt"]

class Papers(ORMBase):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doi: Mapped[str] = mapped_column(Text, unique=True)
    publisher: Mapped[str] = mapped_column(Text)
    title: Mapped[Optional[str]] = mapped_column(Text)
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    format: Mapped[FILEFORMAT]
    date_added: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.date_added is None:
            self.date_added = datetime.now()


class PaperSections(ORMBase):
    __tablename__ = "paper_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True,
                                    autoincrement=True)
    pid: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete='CASCADE'),
                        unique=False, index=True)

    doi: Mapped[str] = mapped_column(Text, index=True)
    format: Mapped[FILEFORMAT]
    type: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)

    date_added: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.date_added is None:
            self.date_added = datetime.now()


if __name__ == "__main__":
    import sett
    from backend import postgres

    sett.load_settings()
    postgres.load_settings()

    # Create all tables if not already created
    ORMBase.metadata.create_all(postgres.engine())
    print("Done!")
