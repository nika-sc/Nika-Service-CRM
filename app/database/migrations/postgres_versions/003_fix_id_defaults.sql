DO $$
DECLARE
    rec RECORD;
    seq_fqname TEXT;
    max_id BIGINT;
BEGIN
    FOR rec IN
        SELECT c.table_name
        FROM information_schema.columns c
        WHERE c.table_schema = 'public'
          AND c.column_name = 'id'
          AND c.data_type IN ('smallint', 'integer', 'bigint')
    LOOP
        seq_fqname := format('public.%I_id_seq', rec.table_name);

        EXECUTE format('CREATE SEQUENCE IF NOT EXISTS %s', seq_fqname);

        EXECUTE format(
            'ALTER TABLE public.%I ALTER COLUMN id SET DEFAULT nextval(''%s''::regclass)',
            rec.table_name,
            seq_fqname
        );

        EXECUTE format('ALTER SEQUENCE %s OWNED BY public.%I.id', seq_fqname, rec.table_name);

        EXECUTE format('SELECT COALESCE(MAX(id), 0) FROM public.%I', rec.table_name) INTO max_id;

        EXECUTE format(
            'SELECT setval(''%s''::regclass, %s, %s)',
            seq_fqname,
            CASE WHEN max_id > 0 THEN max_id ELSE 1 END,
            CASE WHEN max_id > 0 THEN 'true' ELSE 'false' END
        );
    END LOOP;
END $$;
