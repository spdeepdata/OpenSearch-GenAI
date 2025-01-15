graph TD
    subgraph Code Organization
        SL[sharded_loader.py]
        SS[sharded_search.py]
    end

    subgraph Tenant Management
        TM[Tenant Metadata]
        RK[Routing Keys]
    end

    subgraph Elasticsearch Shards
        S1[Shard 1]
        S2[Shard 2]
        S3[Shard 3]
        S4[Shard 4]
        S5[Shard 5]
    end

    subgraph Search Process
        QP[Query Parser]
        RT[Router]
        SR[Search Results]
        MS[Marketplace Results]
    end

    SL --> TM
    TM --> RK
    RK --> RT

    SS --> QP
    QP --> RT
    RT --> |Tenant1 Data|S1
    RT --> |Tenant2 Data|S2
    RT --> |Marketplace Search|S3
    RT --> |Marketplace Search|S4
    RT --> |Marketplace Search|S5

    S1 --> SR
    S2 --> SR
    S3 --> MS
    S4 --> MS
    S5 --> MS