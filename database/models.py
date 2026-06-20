from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class ProductDimension(Base):
    """
    dim_product table storing product metadata.
    """

    __tablename__ = "dim_product"

    sku_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    package_size: Mapped[Optional[str]] = mapped_column(String(50))
    launch_date: Mapped[Optional[date]] = mapped_column(Date)

    # Relationships
    sales: Mapped[list["SalesFact"]] = relationship(back_populates="product")


class StoreDimension(Base):
    """
    dim_store table storing store and regional geography.
    """

    __tablename__ = "dim_store"

    store_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    sales: Mapped[list["SalesFact"]] = relationship(back_populates="store")


class DateDimension(Base):
    """
    dim_date table storing date configurations for dimensional modeling.
    """

    __tablename__ = "dim_date"

    date_key: Mapped[date] = mapped_column(Date, primary_key=True)
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    season: Mapped[str] = mapped_column(String(20), nullable=False)


class SalesFact(Base):
    """
    fact_sales table storing daily transactions.
    """

    __tablename__ = "fact_sales"

    transaction_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    transaction_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    sku_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("dim_product.sku_id"), nullable=False
    )
    store_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("dim_store.store_id"), nullable=False
    )
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("customer_master.customer_id"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    revenue: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    # Relationships
    product: Mapped["ProductDimension"] = relationship(back_populates="sales")
    store: Mapped["StoreDimension"] = relationship(back_populates="sales")
    customer: Mapped[Optional["CustomerMaster"]] = relationship(back_populates="sales")


class ForecastResult(Base):
    """
    forecast_results table storing Prophet predicted metrics.
    """

    __tablename__ = "forecast_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    predicted_revenue: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prediction_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class UploadAudit(Base):
    """
    upload_audit table storing audit logs for CSV ingestion processes.
    """

    __tablename__ = "upload_audit"

    upload_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_table: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    inserted_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    removed_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    final_loaded_rows: Mapped[int] = mapped_column(Integer, default=0)
    upload_status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000))
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class CustomerMaster(Base):
    """
    customer_master table storing customer records.
    """

    __tablename__ = "customer_master"

    customer_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Relationships
    sales: Mapped[list["SalesFact"]] = relationship(back_populates="customer")
