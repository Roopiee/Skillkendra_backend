-- Run this script as the database superuser (or the owner of the skillkendra schema)

-- 1. Add course_name and issue_date to extractions (if missing)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='skillkendra' AND table_name='extractions' AND column_name='course_name') THEN
        ALTER TABLE skillkendra.extractions ADD COLUMN course_name TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='skillkendra' AND table_name='extractions' AND column_name='issue_date') THEN
        ALTER TABLE skillkendra.extractions ADD COLUMN issue_date TEXT;
    END IF;
END $$;

-- 2. Fix column types: course_name was CHAR(1), issue_date was DATE — both must be TEXT
DO $$
BEGIN
    IF (SELECT data_type FROM information_schema.columns WHERE table_schema='skillkendra' AND table_name='extractions' AND column_name='course_name') != 'text' THEN
        ALTER TABLE skillkendra.extractions ALTER COLUMN course_name TYPE TEXT;
    END IF;
    IF (SELECT data_type FROM information_schema.columns WHERE table_schema='skillkendra' AND table_name='extractions' AND column_name='issue_date') != 'text' THEN
        ALTER TABLE skillkendra.extractions ALTER COLUMN issue_date TYPE TEXT;
    END IF;
END $$;

-- 2. Add unique constraint to KYC documents
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_constraint 
        WHERE conname = 'kyc_documents_session_id_key' 
        AND conrelid = 'skillkendra.kyc_documents'::regclass
    ) THEN
        ALTER TABLE skillkendra.kyc_documents ADD CONSTRAINT kyc_documents_session_id_key UNIQUE (session_id);
    END IF;
END $$;

-- 3. (Optional) Grant dev-user table ownership or robust permissions
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA skillkendra TO "dev-user";
