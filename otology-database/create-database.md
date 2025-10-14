# 创建 examination_record

```sql
CREATE TABLE IF NOT EXISTS examination_record (
"repo" VARCHAR(50) PRIMARY KEY,
"repdr" VARCHAR(50),
"checkitem" VARCHAR(255),
"repdate" DATE,
"series" VARCHAR(20),
"mrn" VARCHAR(50),
"name" VARCHAR(50),
"picdir" VARCHAR(255)
)
```

# 数据库触发器  name 列

当 examination_record 表每次插入新行时
根据插入行的 mrn 去 patient_admission_record 查找对应病人姓名
并把 name 写入 examination_record 的 name 字段。

postgresql里的 Query SQL 输入

```sql
-- 1) 确保 examination_record 有 name 字段

ALTER TABLE examination_record
    ADD COLUMN IF NOT EXISTS name text;

-- 2) 创建触发器函数：在插入或更新 mrn 时自动回填 name

CREATE OR REPLACE FUNCTION trg_examination_record_fill_name()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    -- 仅当 mrn 存在或变动时处理
    IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND NEW.mrn IS DISTINCT FROM OLD.mrn) THEN
        SELECT par.name
        INTO NEW.name
        FROM patient_admission_record AS par
        WHERE par.mrn = NEW.mrn;

        -- 如果没有匹配，决定策略：可置为空或报错
        IF NEW.name IS NULL THEN
            -- 方案 A：允许为空（静默）
            -- RETURN NEW;

            -- 方案 B：报错，强制必须存在映射
            RAISE EXCEPTION 'No patient name found for mrn=%', NEW.mrn
                USING ERRCODE = 'foreign_key_violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- 3) 安装触发器：插入前、更新 mrn 前执行

CREATE TRIGGER before_insupd_fill_name
BEFORE INSERT OR UPDATE OF mrn ON examination_record
FOR EACH ROW
EXECUTE FUNCTION trg_examination_record_fill_name();
```

# 数据库触发器  picdir 列

当 examination_record 表每次插入新行时
根据插入行的 mrn 去 patient_admission_record 查找对应病人姓名
并把 picdir 写入 examination_record 的 picdir 字段。

postgresql里的 Query SQL 输入

```sql
-- 1) 确保 examination_record 有 picdir 字段

ALTER TABLE examination_record
    ADD COLUMN IF NOT EXISTS picdir text;

-- 2) 创建触发器函数：在插入或更新 mrn 时自动回填 picdir

CREATE OR REPLACE FUNCTION trg_examination_record_fill_picdir()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    -- 仅当 mrn 存在或变动时处理
    IF TG_OP = 'INSERT' OR (TG_OP = 'UPDATE' AND NEW.mrn IS DISTINCT FROM OLD.mrn) THEN
        SELECT par.picdir
        INTO NEW.picdir
        FROM patient_admission_record AS par
        WHERE par.mrn = NEW.mrn;

        -- 如果没有匹配，决定策略：可置为空或报错
        IF NEW.picdir IS NULL THEN
            -- 方案 A：允许为空（静默）
            -- RETURN NEW;

            -- 方案 B：报错，强制必须存在映射
            RAISE EXCEPTION 'No patient picdir found for mrn=%', NEW.mrn
                USING ERRCODE = 'foreign_key_violation';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- 3) 安装触发器：插入前、更新 mrn 前执行

CREATE TRIGGER before_insupd_fill_picdir
BEFORE INSERT OR UPDATE OF mrn ON examination_record
FOR EACH ROW
EXECUTE FUNCTION trg_examination_record_fill_picdir();
```

# examination_record 自动新增 picname 列

```sql
ALTER TABLE examination_record
ADD COLUMN picname text GENERATED ALWAYS AS (
    COALESCE(extract(year  from repdate)::int::text, '') || '-' ||
    LPAD((extract(month from repdate)::int)::text, 2, '0') || '-' ||
    LPAD((extract(day   from repdate)::int)::text, 2, '0') || '-' ||
    COALESCE(checkitem, '') || '-' ||
    COALESCE(mrn, '')       || '-' ||
    COALESCE(name, '')      || '-' ||
    COALESCE(repo, '')
) STORED;
```

# examination_record 自动新增 picurl 列

```sql
ALTER TABLE examination_record
ADD COLUMN picurl text GENERATED ALWAYS AS (
    '[{"path":"download/noco/' || 
    REPLACE(COALESCE(picdir, ''), '\', '/') || 
    '/' || 
    COALESCE(extract(year  from repdate)::int::text, '') || '-' ||
    LPAD((extract(month from repdate)::int)::text, 2, '0') || '-' ||
    LPAD((extract(day   from repdate)::int)::text, 2, '0') || '-' ||
    COALESCE(checkitem, '') || '-' ||
    COALESCE(mrn, '') || '-' ||
    COALESCE(name, '') || '-' ||
    COALESCE(repo, '') ||
    '.jpg","title":"' || 
    COALESCE(extract(year  from repdate)::int::text, '') || '-' ||
    LPAD((extract(month from repdate)::int)::text, 2, '0') || '-' ||
    LPAD((extract(day   from repdate)::int)::text, 2, '0') || '-' ||
    COALESCE(checkitem, '') || '-' ||
    COALESCE(mrn, '') || '-' ||
    COALESCE(name, '') || '-' ||
    COALESCE(repo, '') ||
    '.jpg","mimetype":"text/html","id":"' || 
    COALESCE(repo, '') || 
    '"}]'
) STORED;
```

# 新增一列 islocalimageexist

```sql
-- 1) 定义枚举类型（如果还未创建过）
CREATE TYPE islocalimageexist_enum AS ENUM ('true', 'false', 'lost');

-- 2) 在 examination_record 表中新增列，使用该枚举类型
ALTER TABLE examination_record
    ADD COLUMN "isLocalImageExist" islocalimageexist_enum;

-- 3) 可选：设置默认值（例如默认 'false'）
ALTER TABLE examination_record
    ALTER COLUMN "isLocalImageExist" SET DEFAULT 'false';

-- 4) 可选：为现有行填充默认值
UPDATE examination_record
SET "isLocalImageExist" = 'false'
WHERE "isLocalImageExist" IS NULL;
```

# 新增听力数据列

```sql
ALTER TABLE examination_record
    ADD COLUMN "b250" INTEGER,
    ADD COLUMN "b500" INTEGER,
    ADD COLUMN "b1k" INTEGER,
    ADD COLUMN "b2k" INTEGER,
    ADD COLUMN "b4k" INTEGER,
    ADD COLUMN "a125" INTEGER,
    ADD COLUMN "a250" INTEGER,
    ADD COLUMN "a500" INTEGER,
    ADD COLUMN "a1k" INTEGER,
    ADD COLUMN "a2k" INTEGER,
    ADD COLUMN "a4k" INTEGER,
    ADD COLUMN "a8k" INTEGER
```

# 新增一列 isAudiogramType

```sql
-- 1) 定义枚举类型（如果还未创建过）
CREATE TYPE isAudiogramType_enum AS ENUM ('auto', 'manual', 'otherhospital', 'unprocessed', 'none');

-- 2) 在 examination_record 表中新增列，使用该枚举类型
ALTER TABLE examination_record
    ADD COLUMN "isAudiogramType" isAudiogramType_enum;

-- 3) 创建触发器函数：根据 checkitem 内容自动设置 isAudiogramType 默认值
CREATE OR REPLACE FUNCTION trg_examination_record_fill_isAudiogramType()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    -- 仅当 isAudiogramType 未设置时处理
    IF TG_OP = 'INSERT' AND NEW."isAudiogramType" IS NULL THEN
        -- 如果 checkitem 包含 "纯音"，则设置为 "unprocessed"
        IF NEW.checkitem IS NOT NULL AND NEW.checkitem LIKE '%纯音%' THEN
            NEW."isAudiogramType" := 'unprocessed'::isAudiogramType_enum;
        ELSE
            -- 其余情况设置为 "none"
            NEW."isAudiogramType" := 'none'::isAudiogramType_enum;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- 4) 安装触发器：插入前执行
CREATE TRIGGER before_insert_fill_isAudiogramType
BEFORE INSERT ON examination_record
FOR EACH ROW
EXECUTE FUNCTION trg_examination_record_fill_isAudiogramType();

-- 5) 为现有行填充默认值（根据 checkitem 内容）
UPDATE examination_record
SET "isAudiogramType" = CASE 
    WHEN checkitem LIKE '%纯音%' THEN 'unprocessed'::isAudiogramType_enum
    ELSE 'none'::isAudiogramType_enum
END
WHERE "isAudiogramType" IS NULL;
```