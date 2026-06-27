"""
算法2 — RFM 用户分群引擎
基于用户消费数据计算 R(Recency)/F(Frequency)/M(Monetary)，
完成用户价值分层、购买力评级、复购率与留存率计算。
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config import (
    DEFAULT_SCORING_METHOD,
    FIXED_THRESHOLDS,
    PURCHASING_POWER_MAP,
    RFM_SEGMENT_THRESHOLD,
    SEGMENT_DEFINITIONS,
)

logger = logging.getLogger(__name__)


@dataclass
class RFMResult:
    """单用户 RFM 计算结果"""
    user_id: int
    recency: int
    frequency: int
    monetary: float
    r_score: int
    f_score: int
    m_score: int
    rfm_segment: str
    rfm_group: str
    purchasing_power: str

    def to_db_row(self, compute_batch: str) -> Tuple:
        return (
            self.user_id,
            self.recency,
            self.frequency,
            self.monetary,
            self.r_score,
            self.f_score,
            self.m_score,
            self.rfm_segment,
            self.rfm_group,
            compute_batch,
        )


@dataclass
class RFMSummary:
    """RFM 汇总指标"""
    total_users: int
    # 分层统计
    segment_counts: Dict[str, int]                # 各分层用户数
    segment_percents: Dict[str, float]             # 各分层占比
    segment_avg_monetary: Dict[str, float]          # 各分层平均消费金额
    # 购买力统计
    purchasing_power_counts: Dict[str, int]         # 各购买力用户数
    # 复购率
    repurchase_rate: float                           # 复购率 (购买≥2次的用户占比)
    repurchase_users: int                            # 复购用户数
    # 留存率
    retention_rate: Optional[float]                  # 留存率
    retention_users: Optional[int]                   # 留存用户数
    previous_period_users: Optional[int]             # 上期用户数


class RFMEngine:
    """RFM 计算引擎"""

    # ------------------------------------------------------------------
    # 1. 原始 RFM 值计算
    # ------------------------------------------------------------------
    @staticmethod
    def compute_rfm(
        df: pd.DataFrame,
        recency_base_date: str,
    ) -> pd.DataFrame:
        """
        从订单明细计算每用户的 R / F / M 原始值。

        Parameters
        ----------
        df : DataFrame
            订单数据，至少包含 user_id, order_id, order_date, total_amount 列。
        recency_base_date : str
            R 值参照日期，格式 YYYY-MM-DD。

        Returns
        -------
        DataFrame 包含 user_id, recency, frequency, monetary。
        """
        base = pd.Timestamp(recency_base_date)

        rfm = df.groupby("user_id").agg(
            recency=("order_date", lambda s: (base - s.max()).days),
            frequency=("order_id", "nunique"),
            monetary=("total_amount", "sum"),
        ).reset_index()

        rfm["recency"] = rfm["recency"].astype(int)
        rfm["frequency"] = rfm["frequency"].astype(int)
        rfm["monetary"] = rfm["monetary"].round(2)

        logger.info(
            "RFM 原始值计算完成，用户数=%d，recency 范围[%d,%d]，frequency 范围[%d,%d]，monetary 范围[%.2f,%.2f]",
            len(rfm),
            rfm["recency"].min(), rfm["recency"].max(),
            rfm["frequency"].min(), rfm["frequency"].max(),
            rfm["monetary"].min(), rfm["monetary"].max(),
        )
        return rfm

    # ------------------------------------------------------------------
    # 2. R/F/M 评分（1~5，5 最好）
    # ------------------------------------------------------------------
    @staticmethod
    def score_rfm(
        rfm: pd.DataFrame,
        method: str = DEFAULT_SCORING_METHOD,
    ) -> pd.DataFrame:
        """
        对 R / F / M 打分，返回包含 r_score, f_score, m_score 的 DataFrame。

        method='quantile': 五分位数法，等频切分为 5 档。
        method='fixed':    固定阈值法。
        """
        df = rfm.copy()

        if method == "quantile":
            # R 越小越好 → 用 ascending=True 排序后的分位
            try:
                df["r_score"] = pd.qcut(df["recency"], q=5, labels=[5, 4, 3, 2, 1]).astype(int)
            except ValueError:
                # 数据分布不足以切 5 份时降级
                df["r_score"] = pd.cut(df["recency"], bins=5, labels=[5, 4, 3, 2, 1]).astype(int)

            try:
                df["f_score"] = pd.qcut(df["frequency"], q=5, labels=[1, 2, 3, 4, 5]).astype(int)
            except ValueError:
                df["f_score"] = pd.cut(df["frequency"], bins=5, labels=[1, 2, 3, 4, 5]).astype(int)

            df["monetary"] = df["monetary"].astype(float)
            try:
                df["m_score"] = pd.qcut(df["monetary"], q=5, labels=[1, 2, 3, 4, 5]).astype(int)
            except ValueError:
                df["m_score"] = pd.cut(df["monetary"], bins=5, labels=[1, 2, 3, 4, 5]).astype(int)

        elif method == "fixed":
            thresholds = FIXED_THRESHOLDS

            def _score_asc(values, thresholds_asc):
                """值越小分越高（R 用）"""
                scores = np.ones(len(values), dtype=int)
                for i, t in enumerate(thresholds_asc):
                    scores[values <= t] = max(5 - i, 1)
                return scores

            def _score_desc(values, thresholds_desc):
                """值越大分越高（F / M 用）"""
                scores = np.ones(len(values), dtype=int)
                for i, t in enumerate(thresholds_desc):
                    scores[values >= t] = max(5 - i, 1)
                return scores

            df["r_score"] = _score_asc(df["recency"].values, thresholds["recency"])
            df["f_score"] = _score_desc(df["frequency"].values, thresholds["frequency"])
            df["m_score"] = _score_desc(df["monetary"].values, thresholds["monetary"])
        else:
            raise ValueError(f"不支持的评分方法: {method}")

        logger.info("R/F/M 评分完成，方法=%s", method)
        return df

    # ------------------------------------------------------------------
    # 3. 用户分层
    # ------------------------------------------------------------------
    @staticmethod
    def segment_users(df: pd.DataFrame, threshold: int = RFM_SEGMENT_THRESHOLD) -> pd.DataFrame:
        """
        根据 R/F/M 评分完成 8 类用户分层，同时生成：
        - rfm_segment: 中文分层标签
        - rfm_group:   三位数 RFM 组合字符串（如 '555'）
        """
        d = df.copy()
        t = threshold

        d["r_level"] = d["r_score"].apply(lambda x: "高" if x >= t else "低")
        d["f_level"] = d["f_score"].apply(lambda x: "高" if x >= t else "低")
        d["m_level"] = d["m_score"].apply(lambda x: "高" if x >= t else "低")

        d["rfm_segment"] = d.apply(
            lambda r: SEGMENT_DEFINITIONS.get(
                (r["r_level"], r["f_level"], r["m_level"]), "其他客户"
            ),
            axis=1,
        )
        d["rfm_group"] = (
            d["r_score"].astype(str)
            + d["f_score"].astype(str)
            + d["m_score"].astype(str)
        )
        d.drop(columns=["r_level", "f_level", "m_level"], inplace=True)

        seg_counts = d["rfm_segment"].value_counts().to_dict()
        logger.info("用户分层完成，分层分布=%s", seg_counts)
        return d

    # ------------------------------------------------------------------
    # 4. 购买力评级
    # ------------------------------------------------------------------
    @staticmethod
    def classify_purchasing_power(df: pd.DataFrame) -> pd.DataFrame:
        """基于 M 评分分配购买力等级。"""
        d = df.copy()
        d["purchasing_power"] = d["m_score"].map(PURCHASING_POWER_MAP).fillna("未评级")
        logger.info("购买力评级完成")
        return d

    # ------------------------------------------------------------------
    # 5. 复购率
    # ------------------------------------------------------------------
    @staticmethod
    def calc_repurchase_rate(df: pd.DataFrame) -> Tuple[float, int, int]:
        """
        复购率 = 消费次数 ≥ 2 的用户数 / 总用户数。
        返回 (复购率, 复购用户数, 总用户数)。
        """
        total = len(df)
        repurchase = int((df["frequency"] >= 2).sum())
        rate = round(repurchase / total * 100, 2) if total > 0 else 0.0
        logger.info("复购率=%.2f%% (%d/%d)", rate, repurchase, total)
        return rate, repurchase, total

    # ------------------------------------------------------------------
    # 6. 留存率
    # ------------------------------------------------------------------
    @staticmethod
    def calc_retention_rate(
        current_df: pd.DataFrame,
        prev_df: pd.DataFrame,
    ) -> Tuple[float, int, int]:
        """
        留存率 = 两期均活跃的用户数 / 上期活跃用户数 × 100%。

        Parameters
        ----------
        current_df : DataFrame
            当期订单数据。
        prev_df : DataFrame
            上期订单数据。

        Returns
        -------
        (留存率, 留存用户数, 上期总用户数)。
        """
        prev_users = set(prev_df["user_id"].unique())
        curr_users = set(current_df["user_id"].unique())
        retained = prev_users & curr_users
        rate = round(len(retained) / len(prev_users) * 100, 2) if prev_users else 0.0
        logger.info(
            "留存率=%.2f%% (%d/%d)", rate, len(retained), len(prev_users)
        )
        return rate, len(retained), len(prev_users)

    # ------------------------------------------------------------------
    # 7. 生成汇总报告
    # ------------------------------------------------------------------
    @classmethod
    def build_summary(
        cls,
        rfm: pd.DataFrame,
        repurchase_rate: float,
        repurchase_users: int,
        retention_rate: Optional[float] = None,
        retention_users: Optional[int] = None,
        previous_period_users: Optional[int] = None,
    ) -> RFMSummary:
        """汇总分层、购买力、复购率、留存率等全景指标。"""
        total = len(rfm)

        seg_counts = rfm["rfm_segment"].value_counts().to_dict()
        seg_percents = {k: round(v / total * 100, 2) for k, v in seg_counts.items()}
        seg_avg_monetary = (
            rfm.groupby("rfm_segment")["monetary"].mean().round(2).to_dict()
        )

        pp_counts = rfm["purchasing_power"].value_counts().to_dict()

        return RFMSummary(
            total_users=total,
            segment_counts=seg_counts,
            segment_percents=seg_percents,
            segment_avg_monetary=seg_avg_monetary,
            purchasing_power_counts=pp_counts,
            repurchase_rate=repurchase_rate,
            repurchase_users=repurchase_users,
            retention_rate=retention_rate,
            retention_users=retention_users,
            previous_period_users=previous_period_users,
        )

    # ------------------------------------------------------------------
    # 8. 一站式 Pipeline
    # ------------------------------------------------------------------
    @classmethod
    def run(
        cls,
        df: pd.DataFrame,
        recency_base_date: str,
        scoring_method: str = DEFAULT_SCORING_METHOD,
        prev_df: Optional[pd.DataFrame] = None,
    ) -> Tuple[List[RFMResult], RFMSummary]:
        """
        一站式 RFM 分析流水线。

        Parameters
        ----------
        df : DataFrame
            当期订单数据。
        recency_base_date : str
            R 值基准日期。
        scoring_method : str
            评分方式 'quantile' 或 'fixed'。
        prev_df : DataFrame or None
            上期订单数据，用于计算留存率。为 None 则跳过留存率。

        Returns
        -------
        (results, summary): 单用户结果列表 + 汇总指标。
        """
        # Step 1: 计算原始 RFM
        rfm = cls.compute_rfm(df, recency_base_date)
        if len(rfm) == 0:
            return [], RFMSummary(
                total_users=0,
                segment_counts={}, segment_percents={}, segment_avg_monetary={},
                purchasing_power_counts={},
                repurchase_rate=0.0, repurchase_users=0,
                retention_rate=None, retention_users=None, previous_period_users=None,
            )

        # Step 2: 评分
        rfm = cls.score_rfm(rfm, scoring_method)

        # Step 3: 分层
        rfm = cls.segment_users(rfm)

        # Step 4: 购买力评级
        rfm = cls.classify_purchasing_power(rfm)

        # Step 5: 复购率
        rep_rate, rep_users, _ = cls.calc_repurchase_rate(rfm)

        # Step 6: 留存率
        ret_rate = None
        ret_users = None
        prev_count = None
        if prev_df is not None and len(prev_df) > 0:
            ret_rate, ret_users, prev_count = cls.calc_retention_rate(df, prev_df)

        # Step 7: 汇总
        summary = cls.build_summary(
            rfm, rep_rate, rep_users, ret_rate, ret_users, prev_count
        )

        # Step 8: 组装结果
        results = [
            RFMResult(
                user_id=int(row["user_id"]),
                recency=int(row["recency"]),
                frequency=int(row["frequency"]),
                monetary=float(row["monetary"]),
                r_score=int(row["r_score"]),
                f_score=int(row["f_score"]),
                m_score=int(row["m_score"]),
                rfm_segment=str(row["rfm_segment"]),
                rfm_group=str(row["rfm_group"]),
                purchasing_power=str(row["purchasing_power"]),
            )
            for _, row in rfm.iterrows()
        ]

        logger.info(
            "RFM Pipeline 完成：%d 用户，%d 分层，复购率 %.2f%%，留存率 %s",
            len(results),
            len(summary.segment_counts),
            summary.repurchase_rate,
            f"{summary.retention_rate:.2f}%" if summary.retention_rate is not None else "未计算",
        )
        return results, summary
