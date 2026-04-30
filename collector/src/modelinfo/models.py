from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    OPEN_SOURCE = "open_source"
    CLOSED = "closed"


class ModelStatus(str, Enum):
    ACTIVE = "active"
    BETA = "beta"
    DEPRECATED = "deprecated"
    COMING_SOON = "coming_soon"


class Channel(str, Enum):
    OFFICIAL = "official"
    MARKETPLACE = "marketplace"
    RESELLER = "reseller"


class ReasoningLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Capabilities(BaseModel):
    text: bool = False
    code: bool = False
    reasoning: bool = False
    vision: bool = False
    image_gen: bool = False
    audio: bool = False
    audio_gen: bool = False
    video: bool = False
    tool_use: bool = False
    structured_output: bool = False
    streaming: bool = False
    batch: bool = False
    fine_tuning: bool = False
    embedding: bool = False


class Urls(BaseModel):
    official: Optional[str] = None
    docs: Optional[str] = None
    pricing: Optional[str] = None


class ModelInfo(BaseModel):
    model_id: str
    model_name: str
    provider: str
    provider_type: Optional[ProviderType] = None
    release_date: Optional[date] = None
    status: ModelStatus = ModelStatus.ACTIVE
    aliases: list[str] = Field(default_factory=list)
    capabilities: Capabilities = Field(default_factory=Capabilities)
    context_length: Optional[int] = None
    max_output_tokens: Optional[int] = None
    regions: list[str] = Field(default_factory=list)
    private_deployment: bool = False
    openai_compatible: bool = False
    urls: Urls = Field(default_factory=Urls)
    tags: list[str] = Field(default_factory=list)
    last_updated: Optional[datetime] = None


class PricingInfo(BaseModel):
    pricing_id: str
    model_id: str
    channel: Channel = Channel.OFFICIAL
    market_name: Optional[str] = None
    region: str = "global"
    valid_from: date
    currency: str = "USD"
    input_price_per_1m: Optional[float] = None
    output_price_per_1m: Optional[float] = None
    cache_read_price_per_1m: Optional[float] = None
    cache_write_price_per_1m: Optional[float] = None
    reasoning_tokens_charged: bool = False
    reasoning_overhead_ratio: Optional[float] = None
    price_per_request: Optional[float] = None
    price_per_image: Optional[float] = None
    price_per_audio_min: Optional[float] = None
    tiers: Optional[dict] = None
    volume_discount: Optional[dict] = None
    reserved_discount_pct: Optional[float] = None
    free_tier_tokens: Optional[int] = None
    min_billable_tokens: Optional[int] = None
    rounding_unit: Optional[int] = None
    has_spot: bool = False
    source: Optional[str] = None
    last_verified: Optional[datetime] = None


class EvalInfo(BaseModel):
    eval_id: str
    model_id: str
    eval_date: date
    source: str
    mmlu: Optional[float] = None
    gsm8k: Optional[float] = None
    humaneval: Optional[float] = None
    other_benchmarks: Optional[dict] = None
    tokens_per_second: Optional[int] = None
    avg_latency_ms: Optional[int] = None
    p95_latency_ms: Optional[int] = None
    reasoning_level: Optional[ReasoningLevel] = None
    overall_score: Optional[float] = None
    cost_efficiency_score: Optional[float] = None


class ChangeRecord(BaseModel):
    table_name: str
    model_id: str
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_at: datetime = Field(default_factory=datetime.now)
    source_url: Optional[str] = None
