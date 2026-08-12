"""Small, conservative robots.txt policy for selective crawling."""

from dataclasses import dataclass
from urllib.robotparser import RobotFileParser


@dataclass(slots=True)
class RobotsPolicy:
    parser: RobotFileParser | None = None
    available: bool = False
    error: str | None = None

    @classmethod
    def from_text(cls, robots_url: str, text: str) -> "RobotsPolicy":
        parser = RobotFileParser(robots_url)
        try:
            parser.parse(text.splitlines())
        except Exception as exc:
            return cls(error=f"invalid robots.txt: {exc}")
        return cls(parser=parser, available=True)

    def allows(self, url: str, user_agent: str) -> bool:
        if self.parser is None:
            return True
        return self.parser.can_fetch(user_agent, url)
