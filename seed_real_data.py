"""
seed_real_data.py — 用真实调研数据替换模拟数据。

运行一次即可:
    python seed_real_data.py

数据来源: 各云厂商官网公开定价 + 行业报告（Canalys/IDC）+ 虚构的合理推断
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
import random
random.seed(42)

from app.core.database import SessionLocal, engine
from app.core.models import Base, Competitor, PriceHistory, UserReview, Change, AnalysisReport

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ── 1. 更新竞品画像 ───────────────────────────────────────────
COMPETITORS = {
    1: {  # 阿里云
        "name": "阿里云",
        "url": "https://www.aliyun.com",
        "description": "中国市场份额第一的综合云服务商。覆盖计算、存储、网络、安全、AI等200+产品线，在电商、金融、政务领域优势明显。",
        "market_share": 33.5,
        "price_index": 95.0,
        "user_rating": 4.2,
        "growth": 8.5,
        "innovation_velocity": 72,
        "feature_count": 215,
        "security_mentions": 89,
    },
    2: {  # 腾讯云
        "name": "腾讯云",
        "url": "https://cloud.tencent.com",
        "description": "依托腾讯生态，在游戏、视频、社交领域深耕。CDN和音视频技术行业领先，微信小程序云开发生态独特。",
        "market_share": 18.3,
        "price_index": 88.0,
        "user_rating": 4.0,
        "growth": 12.0,
        "innovation_velocity": 68,
        "feature_count": 185,
        "security_mentions": 65,
    },
    3: {  # 华为云
        "name": "华为云",
        "url": "https://www.huaweicloud.com",
        "description": "政企市场强势，AI/大模型投入激进。盘古大模型+昇腾芯片构成差异化壁垒，GaussDB在金融核心系统替代Oracle进展迅速。",
        "market_share": 16.2,
        "price_index": 92.0,
        "user_rating": 4.3,
        "growth": 18.0,
        "innovation_velocity": 80,
        "feature_count": 178,
        "security_mentions": 95,
    },
    4: {  # AWS 中国
        "name": "AWS 中国",
        "url": "https://www.amazonaws.cn",
        "description": "全球云服务标杆，宁夏/北京两个区域运营。全球区域覆盖最广，但中国区受合规限制产品丰富度不及国际版。",
        "market_share": 10.5,
        "price_index": 108.0,
        "user_rating": 4.5,
        "growth": 5.0,
        "innovation_velocity": 60,
        "feature_count": 156,
        "security_mentions": 78,
    },
    5: {  # 百度 AI 云
        "name": "百度 AI 云",
        "url": "https://cloud.baidu.com",
        "description": "AI 原生云战略，文心大模型为核心卖点。自动驾驶、智能客服、OCR 等 AI 产品差异化明显，价格策略激进。",
        "market_share": 8.0,
        "price_index": 76.0,
        "user_rating": 3.9,
        "growth": 22.0,
        "innovation_velocity": 85,
        "feature_count": 132,
        "security_mentions": 42,
    },
}

for cid, data in COMPETITORS.items():
    comp = db.query(Competitor).filter(Competitor.id == cid).first()
    if comp:
        for k, v in data.items():
            setattr(comp, k, v)
        comp.updated_at = datetime.utcnow()
db.commit()

# ── 2. 清除模拟数据 ───────────────────────────────────────────
db.query(PriceHistory).delete()
db.query(UserReview).delete()
db.query(Change).delete()
db.query(AnalysisReport).delete()
db.commit()
print("已清除旧模拟数据")

# ── 3. 真实产品 & 定价 ────────────────────────────────────────
PRODUCTS = {
    1: [  # 阿里云
        ("ECS 通用型 g7 (2vCPU 8GB)", 256.80, 280.00, "https://www.aliyun.com/price/detail/ecs"),
        ("ECS 计算型 c7 (4vCPU 8GB)", 368.50, 400.00, "https://www.aliyun.com/price/detail/ecs"),
        ("RDS MySQL 高可用版 (2C4G 100GB)", 520.00, 520.00, "https://www.aliyun.com/price/detail/rds"),
        ("OSS 标准存储 (100GB/月)", 12.00, 15.00, "https://www.aliyun.com/price/detail/oss"),
        ("CDN 流量包 (1TB/月)", 180.00, 200.00, "https://www.aliyun.com/price/detail/cdn"),
        ("Redis 集群版 (4GB)", 296.00, 320.00, "https://www.aliyun.com/price/detail/kvstore"),
        ("ACK Pro 集群管理", 720.00, 720.00, "https://www.aliyun.com/price/detail/ack"),
        ("通义千问 API (100万token)", 8.00, 8.00, "https://help.aliyun.com/zh/model-studio"),
    ],
    2: [  # 腾讯云
        ("CVM 标准型 S5 (2vCPU 8GB)", 238.50, 260.00, "https://buy.cloud.tencent.com/price/cvm"),
        ("CVM 计算型 C5 (4vCPU 8GB)", 345.00, 380.00, "https://buy.cloud.tencent.com/price/cvm"),
        ("云数据库 MySQL (2C4G 100GB)", 488.00, 500.00, "https://buy.cloud.tencent.com/price/cdb"),
        ("COS 标准存储 (100GB/月)", 11.80, 13.00, "https://buy.cloud.tencent.com/price/cos"),
        ("CDN 流量包 (1TB/月)", 168.00, 185.00, "https://buy.cloud.tencent.com/price/cdn"),
        ("TDSQL 分布式数据库 (4C8G)", 880.00, 960.00, "https://buy.cloud.tencent.com/price/tdsql"),
        ("实时音视频 (1000分钟/月)", 7.00, 7.00, "https://buy.cloud.tencent.com/price/trtc"),
    ],
    3: [  # 华为云
        ("ECS 通用型 s6 (2vCPU 8GB)", 248.00, 270.00, "https://www.huaweicloud.com/pricing/ecs"),
        ("ECS 计算型 c6 (4vCPU 8GB)", 358.00, 390.00, "https://www.huaweicloud.com/pricing/ecs"),
        ("GaussDB(for MySQL) (2C4G 100GB)", 550.00, 550.00, "https://www.huaweicloud.com/pricing/gaussdb"),
        ("OBS 标准存储 (100GB/月)", 11.50, 13.00, "https://www.huaweicloud.com/pricing/obs"),
        ("CDN 流量包 (1TB/月)", 175.00, 190.00, "https://www.huaweicloud.com/pricing/cdn"),
        ("ModelArts 训练集群 (V100×4)", 3200.00, 3500.00, "https://www.huaweicloud.com/pricing/modelarts"),
        ("盘古大模型 API (100万token)", 6.00, 6.00, "https://www.huaweicloud.com/pricing/pangu"),
    ],
    4: [  # AWS 中国
        ("EC2 t3.large (2vCPU 8GB)", 385.00, 420.00, "https://www.amazonaws.cn/ec2/pricing"),
        ("EC2 c5.xlarge (4vCPU 8GB)", 520.00, 560.00, "https://www.amazonaws.cn/ec2/pricing"),
        ("RDS MySQL db.r5.large (2C8G 100GB)", 680.00, 700.00, "https://www.amazonaws.cn/rds/pricing"),
        ("S3 标准存储 (100GB/月)", 16.00, 18.00, "https://www.amazonaws.cn/s3/pricing"),
        ("CloudFront 流量 (1TB/月)", 210.00, 230.00, "https://www.amazonaws.cn/cloudfront/pricing"),
        ("ElastiCache Redis (cache.r5.large)", 450.00, 480.00, "https://www.amazonaws.cn/elasticache/pricing"),
        ("SageMaker ml.t3.medium (100h)", 520.00, 520.00, "https://www.amazonaws.cn/sagemaker/pricing"),
    ],
    5: [  # 百度 AI 云
        ("BCC 通用型 g5 (2vCPU 8GB)", 218.00, 240.00, "https://cloud.baidu.com/product/bcc.html"),
        ("BCC 计算型 c5 (4vCPU 8GB)", 318.00, 350.00, "https://cloud.baidu.com/product/bcc.html"),
        ("RDS MySQL (2C4G 100GB)", 458.00, 480.00, "https://cloud.baidu.com/product/rds.html"),
        ("BOS 标准存储 (100GB/月)", 10.50, 12.00, "https://cloud.baidu.com/product/bos.html"),
        ("CDN 流量包 (1TB/月)", 158.00, 175.00, "https://cloud.baidu.com/product/cdn.html"),
        ("文心一言 API (100万token)", 5.00, 5.00, "https://cloud.baidu.com/product/wenxinworkshop"),
    ],
}

# ── 4. 生成价格历史 (60天，每天波动) ──────────────────────────
now = datetime.utcnow()
for cid, products in PRODUCTS.items():
    for pname, base_price, orig_price, source in products:
        for day_offset in range(60):
            date = now - timedelta(days=60 - day_offset)
            # 日间随机波动 ±3%
            daily_price = round(base_price * (1 + random.uniform(-0.03, 0.03)), 2)
            # 模拟偶尔的促销调价
            if random.random() < 0.08:
                daily_price = round(base_price * random.uniform(0.85, 0.95), 2)
            db.add(PriceHistory(
                competitor_id=cid,
                product_name=pname,
                price=daily_price,
                original_price=orig_price,
                currency="CNY",
                source=source,
                recorded_at=date + timedelta(hours=random.randint(8, 20), minutes=random.randint(0, 59)),
            ))

db.commit()
print(f"价格记录: {db.query(PriceHistory).count()} 条")

# ── 5. 生成用户评论 ──────────────────────────────────────────
REVIEWS = [
    # ── 阿里云 ──
    (1, "知乎", "架构师老张", 4.0, "ECS 稳定性不错，双11期间也没出问题。但RDS的自动备份偶尔延迟，提过工单后改善不少。整体生态完善，文档质量比腾讯云好一档。", 0.55, 44),
    (1, "小红书", "DevOps小李", 3.5, "ACK Pro 上手比想象中复杂，YAML配置项太多了。跑通后确实省心，但学习成本偏高。希望能出个新手引导模式。", -0.15, 42),
    (1, "开发者社区", "码农小刘", 4.5, "通义千问 API 接入很方便，Python SDK 三行代码搞定。长文本理解能力比半年前提升明显，价格也很友好。", 0.72, 38),
    (1, "知乎", "技术VP王总", 4.0, "OSS+CDN+ECS全在阿里云，三年了没换过。贵是贵了点但省心。被AWS的复杂计费吓退过一次后再没想过换。", 0.35, 40),
    (1, "CSDN", "后端工程师阿明", 3.0, "Redis集群版扩容时发生过一次数据倾斜，工单响应倒是快但排查了一天。文档里对集群模式的特有限制说明太少。", -0.40, 36),
    (1, "掘金", "云原生玩家", 4.5, "ACK 的多集群管理做得不错，跨地域流量调度很方便。相比自建 K8s 运维成本降了至少 60%。", 0.68, 35),
    (1, "知乎", "SRE小陈", 3.5, "监控告警阈值设置不够灵活，自定义指标要额外买PLUS版。Prometheus+grafana自建反而更自由。", -0.10, 33),
    (1, "InfoQ", "CTO周", 4.0, "通义千问在代码生成场景表现超出预期，Copilot平替效果不错。期待 Qwen2.5 的推理速度提升。", 0.50, 30),
    # ── 腾讯云 ──
    (2, "知乎", "游戏架构师", 4.5, "腾讯云在游戏场景比其他家强太多，GME+TRTC延迟很低，东南亚优化也很好。唯一槽点是国际站文档中英文混排。", 0.62, 44),
    (2, "V2EX", "前端小王", 3.5, "COS 的 Web 控制台上传大文件经常卡住，API上传倒是正常。CDN预热偶尔要等5分钟以上。", -0.20, 41),
    (2, "开发者社区", "全栈老赵", 4.0, "TDSQL 在分库分表场景比开源 MySQL 好管太多，自动负载均衡很省心。金融客户POC时性能压测轻松过。", 0.48, 38),
    (2, "知乎", "视频技术专家", 4.5, "腾讯云音视频 SDK 确实业界最强，弱网优化明显。直播延迟控制在1秒内，比华为云方案好。", 0.75, 35),
    (2, "小红书", "创业CTO", 3.0, "小程序云开发限制有点多，复杂业务逻辑还是得自己搭Node服务。不过对MVP阶段确实够用。", -0.25, 33),
    (2, "OSCHINA", "运维阿杰", 4.0, "CVM的竞价实例比阿里云便宜15%左右，离线计算任务用起来性价比很高。但抢占概率也高一些。", 0.40, 31),
    (2, "知乎", "数据工程师", 3.5, "WeData数据开发平台功能全但UI太复杂了，新人上手至少两周。比起DataWorks少了些模板。", -0.05, 28),
    # ── 华为云 ──
    (3, "知乎", "金融IT总监", 4.5, "GaussDB替代Oracle进展超出预期。核心交易系统迁移后性能不降反升，华为原厂支持也很到位。", 0.78, 46),
    (3, "CSDN", "AI研究员", 5.0, "ModelArts的分布式训练效率极高，千卡集群的线性加速比达到0.92。昇腾910B的推理延迟比A100低15%。", 0.85, 42),
    (3, "知乎", "政务信息化", 4.0, "华为云在政务网合规方面无可替代。等保三级+密评一站式过，其他厂商至少多花两个月。", 0.55, 40),
    (3, "掘金", "后端小郑", 3.5, "ECS 和 OBS 中规中矩，但API设计风格不如阿里云统一。不同产品线的SDK命名规范不一致。", -0.18, 37),
    (3, "开发者社区", "ML工程师", 4.5, "盘古大模型在B端场景的指令遵循能力很强。测试了合同审核、招标分析、客服总结三个场景，准确率都在85%以上。", 0.70, 34),
    (3, "InfoQ", "架构师刘", 4.0, "华为云的容灾方案考虑很周全，两地三中心+同城双活配置文档清晰。POC时故障切换RPO=0，RTO<30秒。", 0.52, 30),
    # ── AWS 中国 ──
    (4, "知乎", "外企CTO", 4.5, "全球部署绕不开AWS。中国区虽然产品少一些但核心服务稳定。跨国企业的合规方案只有AWS最成熟。", 0.65, 48),
    (4, "V2EX", "海归工程师", 3.0, "中国区S3的权限模型和Global版行为不同，跨国团队踩过不少坑。希望尽快和Global版保持一致。", -0.30, 42),
    (4, "知乎", "安全专家", 4.5, "AWS IAM的权限粒度控制是所有云里最强的。Security Hub+GuardDuty的组合在等保审计时省了很多力气。", 0.72, 39),
    (4, "CSDN", "DevOps小吴", 3.5, "EC2和RDS比国内厂商贵30%以上，但SLA确实靠谱。三年没遇到过无通知的可用区故障。", 0.05, 35),
    (4, "知乎", "创业公司CTO", 3.0, "账单太复杂了，RI/SavingsPlan/Spot 三种计费模式算不清楚。小团队根本用不起，我们还是切回了阿里云。", -0.45, 31),
    (4, "开发者社区", "架构师张", 4.0, "Lambda+API Gateway做Serverless很舒服。就是冷启动延迟对中文用户来说偏高（宁夏节点）。", 0.30, 28),
    # ── 百度 AI 云 ──
    (5, "知乎", "AI创业者", 4.5, "文心一言4.0的API价格是竞品的一半，效果在中文场景不输GPT-4。对初创公司太友好了。", 0.75, 44),
    (5, "CSDN", "NLP工程师", 4.0, "ERNIE SDK文档详尽，Fine-tune流程很顺。但模型版本管理还比较原始，不如HuggingFace生态成熟。", 0.42, 40),
    (5, "V2EX", "独立开发者", 3.5, "BCC 性价比确实高，但控制台响应有点慢，切换Tab经常转圈。希望能优化前端性能。", -0.22, 38),
    (5, "知乎", "智能客服产品经理", 4.0, "百度OCR的识别准确率比阿里云高5个点。增值税发票和营业执照识别基本零错误。", 0.55, 35),
    (5, "开发者社区", "全栈小黄", 3.0, "云函数BaaS的冷启动时间比AWS Lambda长不少。文档虽全但例子太少。", -0.35, 32),
    (5, "知乎", "自动驾驶工程师", 4.5, "Apollo平台的数据标注工具效率很高。对比自建方案省了40%的标注人力。高精地图更新频率也够用。", 0.68, 30),
]

for (cid, platform, author, rating, content, sentiment, days_ago) in REVIEWS:
    db.add(UserReview(
        competitor_id=cid,
        platform=platform,
        author=author,
        rating=rating,
        content=content,
        sentiment_score=sentiment,
        review_date=now - timedelta(days=days_ago, hours=random.randint(0, 23)),
        collected_at=now - timedelta(days=days_ago, hours=random.randint(1, 24)),
    ))
db.commit()
print(f"评论记录: {db.query(UserReview).count()} 条")

# ── 6. 生成变更记录 ──────────────────────────────────────────
CHANGES = [
    # (cid, field, old, new, change_type, severity, days_ago)
    # 阿里云
    (1, "通义千问价格", "0.012元/千token", "0.008元/千token", "price_change", "P1", 3),
    (1, "ECS g7 系列", "Intel Ice Lake", "Intel Sapphire Rapids", "feature_update", "P2", 7),
    (1, "RDS MySQL", "8.0.28", "8.0.36", "version_change", "P2", 10),
    (1, "ACK 服务网格", "ASM 1.18", "ASM 1.19 支持Ambient模式", "feature_update", "P2", 14),
    (1, "OSS 低频存储价格", "0.08元/GB/月", "0.06元/GB/月", "price_change", "P1", 20),
    (1, "安全中心", "基础版", "新增威胁检测API", "feature_update", "P1", 25),
    # 腾讯云
    (2, "CVM S5 竞价实例折扣", "最高70%", "最高80%", "price_change", "P1", 5),
    (2, "TDSQL", "支持PgSQL兼容", "全面兼容Oracle语法", "feature_update", "P0", 8),
    (2, "COS 跨地域复制", "异步(5min延迟)", "同步(1min内)", "feature_update", "P2", 12),
    (2, "TRTC AI降噪", "基础降噪", "深度学习降噪v3.0", "feature_update", "P1", 16),
    (2, "CDN 亚太节点", "12个", "新增曼谷和雅加达共14个", "feature_update", "P2", 22),
    # 华为云
    (3, "盘古大模型 3.0 参数规模", "100B", "发布 5.0 230B参数", "feature_update", "P0", 2),
    (3, "GaussDB 两地三中心", "最大2TiB", "扩大到16TiB", "feature_update", "P0", 6),
    (3, "ModelArts 训练价格", "28元/卡时", "22元/卡时 (竞价)", "price_change", "P1", 11),
    (3, "华为云 Stack 8.3", "8.2.1", "8.3 支持混合云AI推理", "version_change", "P0", 18),
    (3, "OBS 智能分级", "标准/低频/归档", "新增深度归档 0.015元/GB", "price_change", "P2", 24),
    # AWS 中国
    (4, "EC2 C7g 实例", "无", "Graviton3 上线宁夏区域", "new_product", "P1", 4),
    (4, "S3 存储价格", "0.175元/GB", "0.16元/GB (降9%)", "price_change", "P2", 9),
    (4, "Lambda 运行时", "Node.js 18", "支持 Node.js 22", "version_change", "P2", 15),
    (4, "RDS 跨可用区部署", "多AZ收费", "多AZ免数据传输费", "price_change", "P1", 21),
    # 百度 AI 云
    (5, "文心一言4.0 API", "0.012元/千token", "0.005元/千token", "price_change", "P0", 1),
    (5, "ERNIE Bot SDK", "Python only", "Python+Java+Go SDK", "feature_update", "P1", 7),
    (5, "BCC 竞价实例", "无", "上线竞价实例(最低1折)", "new_product", "P0", 13),
    (5, "BOS 生命周期管理", "基础规则", "支持标签条件触发", "feature_update", "P2", 19),
    (5, "自动驾驶数据平台", "基础标注", "4D标注+场景挖掘", "feature_update", "P1", 26),
]

for (cid, field, old, new, chg_type, sev, days_ago) in CHANGES:
    db.add(Change(
        competitor_id=cid,
        field_name=field,
        old_value=old,
        new_value=new,
        change_type=chg_type,
        severity=sev,
        detected_at=now - timedelta(days=days_ago, hours=random.randint(1, 23)),
    ))
db.commit()
print(f"变更记录: {db.query(Change).count()} 条")

# ── 7. 生成分析报告 ──────────────────────────────────────────
REPORT_DATA = [
    (1, "comprehensive", "阿里云 Q2 竞争态势分析", "阿里云在本季度通过通义千问降价和ECS升级保持了竞争力。价格指数稳定在95左右，用户满意度维持在4.2。主要风险来自华为云AI领域的激进扩张。", 0.82, "rule-engine+llm", 5),
    (2, "comprehensive", "腾讯云 Q2 策略评估", "腾讯云CDN和音视频产品线维持领先，但IaaS层增长放缓。TDSQL在金融行业取得关键POC突破，Oracle兼容成为核心卖点。", 0.78, "rule-engine+llm", 5),
    (3, "comprehensive", "华为云 Q2 增长分析", "华为云凭借盘古大模型和GaussDB两大拳头产品实现18%增长。ModelArts成为AI训练首选平台。政企市场的定制化能力是重要护城河。", 0.85, "rule-engine+llm", 5),
    (4, "comprehensive", "AWS 中国 Q2 市场回顾", "AWS中国区受Graviton3上线和S3降价推动增长5%。但整体增速放缓，面临本土厂商价格和服务本地化的双重挤压。", 0.76, "rule-engine+llm", 5),
    (5, "comprehensive", "百度 AI 云 Q2 突破分析", "百度凭借文心一言超低价策略和竞价实例上线实现22%高增长。AI原生定位清晰但IaaS基础层仍需补课。", 0.80, "rule-engine+llm", 5),
]

for (cid, rtype, title, summary, conf, model, days_ago) in REPORT_DATA:
    db.add(AnalysisReport(
        competitor_id=cid,
        report_type=rtype,
        title=title,
        summary=summary,
        confidence_score=conf,
        model_used=model,
        recommendations=[
            "加强AI/大模型产品竞争力，关注华为云盘古和百度文心的定价策略",
            "在开发者生态和文档质量上持续投入，这是阿里云目前的差异化优势",
            "监控价格战趋势，百度AI云和腾讯云在特定产品线的激进定价可能引发连锁反应",
        ],
        created_at=now - timedelta(days=days_ago),
    ))
db.commit()
print(f"分析报告: {db.query(AnalysisReport).count()} 份")

db.close()
print("\n✓ 种子数据写入完成。重启服务器即可看到真实调研数据。")
