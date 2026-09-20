-- HoTLinE Doc — โครงสร้างฐานข้อมูล (PostgreSQL)
--
-- ไฟล์นี้สร้างอัตโนมัติ อย่าแก้ด้วยมือ
-- สร้างใหม่ด้วย: cd backend && uv run python -m scripts.dump_schema > ../docs/schema.sql
--
-- คำอธิบายความสัมพันธ์และการนอร์มัลไลเซชันถึง 3NF อยู่ที่ docs/database.md

CREATE TABLE app_user (
	id SERIAL NOT NULL, 
	email VARCHAR(160), 
	phone VARCHAR(20), 
	password_hash VARCHAR(128) NOT NULL, 
	first_name VARCHAR(80) NOT NULL, 
	last_name VARCHAR(80) NOT NULL, 
	national_id VARCHAR(13), 
	role VARCHAR(20) DEFAULT 'operator' NOT NULL, 
	is_active BOOLEAN DEFAULT 'true' NOT NULL, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	pseudonym_code VARCHAR(16), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email), 
	UNIQUE (phone), 
	UNIQUE (national_id), 
	UNIQUE (pseudonym_code)
);

CREATE TABLE issuing_agency (
	id SERIAL NOT NULL, 
	code VARCHAR(24) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	description TEXT, 
	website VARCHAR(200), 
	is_active BOOLEAN DEFAULT 'true' NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE local_authority (
	id SERIAL NOT NULL, 
	code VARCHAR(16) NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	kind VARCHAR(40) NOT NULL, 
	district VARCHAR(60) NOT NULL, 
	address TEXT, 
	phone VARCHAR(40), 
	email VARCHAR(120), 
	office_hours VARCHAR(120), 
	is_active BOOLEAN DEFAULT 'true' NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE property_type (
	id SERIAL NOT NULL, 
	code VARCHAR(20) NOT NULL, 
	name_th VARCHAR(120) NOT NULL, 
	description TEXT, 
	requires_license BOOLEAN DEFAULT 'true' NOT NULL, 
	is_out_of_scope BOOLEAN DEFAULT 'false' NOT NULL, 
	display_order INTEGER DEFAULT '0' NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code)
);

CREATE TABLE audit_log (
	id SERIAL NOT NULL, 
	actor_id INTEGER, 
	action VARCHAR(60) NOT NULL, 
	entity_type VARCHAR(40) NOT NULL, 
	entity_id INTEGER, 
	from_status VARCHAR(24), 
	to_status VARCHAR(24), 
	outcome VARCHAR(12) DEFAULT 'success' NOT NULL, 
	detail TEXT, 
	ip_address VARCHAR(45), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES app_user (id)
);
CREATE INDEX ix_audit_log_actor_id ON audit_log (actor_id);
CREATE INDEX ix_audit_log_entity_id ON audit_log (entity_id);

CREATE TABLE classification_rule (
	id SERIAL NOT NULL, 
	code VARCHAR(32) NOT NULL, 
	property_type_id INTEGER NOT NULL, 
	priority INTEGER NOT NULL, 
	min_rooms INTEGER, 
	max_rooms INTEGER, 
	min_guests INTEGER, 
	max_guests INTEGER, 
	requires_restaurant BOOLEAN, 
	reason_template TEXT NOT NULL, 
	outcome_message TEXT NOT NULL, 
	effective_from DATE NOT NULL, 
	effective_to DATE, 
	is_active BOOLEAN DEFAULT 'true' NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code), 
	FOREIGN KEY(property_type_id) REFERENCES property_type (id)
);

CREATE TABLE contact_point (
	id SERIAL NOT NULL, 
	issuing_agency_id INTEGER NOT NULL, 
	local_authority_id INTEGER, 
	office_name VARCHAR(160) NOT NULL, 
	address TEXT, 
	phone VARCHAR(40), 
	office_hours VARCHAR(120), 
	estimated_days INTEGER, 
	notes TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_contact_agency_authority UNIQUE (issuing_agency_id, local_authority_id), 
	FOREIGN KEY(issuing_agency_id) REFERENCES issuing_agency (id), 
	FOREIGN KEY(local_authority_id) REFERENCES local_authority (id)
);

CREATE TABLE document_type (
	id SERIAL NOT NULL, 
	code VARCHAR(10) NOT NULL, 
	name_th VARCHAR(200) NOT NULL, 
	description TEXT, 
	category VARCHAR(10) NOT NULL, 
	issuing_agency_id INTEGER, 
	preparation_note TEXT, 
	estimated_days INTEGER, 
	is_system_form BOOLEAN DEFAULT 'false' NOT NULL, 
	allows_multiple BOOLEAN DEFAULT 'false' NOT NULL, 
	accepted_mime VARCHAR(200) DEFAULT 'application/pdf,image/jpeg,image/png' NOT NULL, 
	display_order INTEGER DEFAULT '0' NOT NULL, 
	is_active BOOLEAN DEFAULT 'true' NOT NULL, 
	parent_id INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (code), 
	FOREIGN KEY(issuing_agency_id) REFERENCES issuing_agency (id), 
	FOREIGN KEY(parent_id) REFERENCES document_type (id)
);

CREATE TABLE fee_schedule (
	id SERIAL NOT NULL, 
	property_type_id INTEGER NOT NULL, 
	amount NUMERIC(12, 2) NOT NULL, 
	currency VARCHAR(3) DEFAULT 'THB' NOT NULL, 
	validity_years INTEGER NOT NULL, 
	effective_from DATE NOT NULL, 
	effective_to DATE, 
	is_active BOOLEAN DEFAULT 'true' NOT NULL, 
	note TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(property_type_id) REFERENCES property_type (id)
);

CREATE TABLE officer_assignment (
	id SERIAL NOT NULL, 
	officer_id INTEGER NOT NULL, 
	local_authority_id INTEGER NOT NULL, 
	is_active BOOLEAN DEFAULT 'true' NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_officer_authority UNIQUE (officer_id, local_authority_id), 
	FOREIGN KEY(officer_id) REFERENCES app_user (id), 
	FOREIGN KEY(local_authority_id) REFERENCES local_authority (id)
);

CREATE TABLE operator (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	display_name VARCHAR(160) NOT NULL, 
	is_juristic BOOLEAN DEFAULT 'false' NOT NULL, 
	juristic_reg_no VARCHAR(20), 
	contact_phone VARCHAR(20), 
	contact_email VARCHAR(160), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES app_user (id)
);

CREATE TABLE document_requirement (
	id SERIAL NOT NULL, 
	property_type_id INTEGER NOT NULL, 
	document_type_id INTEGER NOT NULL, 
	is_mandatory BOOLEAN DEFAULT 'true' NOT NULL, 
	display_order INTEGER DEFAULT '0' NOT NULL, 
	note TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_requirement_type_doc UNIQUE (property_type_id, document_type_id), 
	FOREIGN KEY(property_type_id) REFERENCES property_type (id), 
	FOREIGN KEY(document_type_id) REFERENCES document_type (id)
);

CREATE TABLE property (
	id SERIAL NOT NULL, 
	operator_id INTEGER NOT NULL, 
	local_authority_id INTEGER NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	address_no VARCHAR(40) NOT NULL, 
	moo VARCHAR(20), 
	soi VARCHAR(80), 
	road VARCHAR(80), 
	sub_district VARCHAR(80) NOT NULL, 
	district VARCHAR(80) NOT NULL, 
	province VARCHAR(80) NOT NULL, 
	postal_code VARCHAR(5) NOT NULL, 
	room_count INTEGER NOT NULL, 
	max_guests INTEGER NOT NULL, 
	has_restaurant BOOLEAN DEFAULT 'false' NOT NULL, 
	accommodation_kind VARCHAR(24), 
	accommodation_kind_other VARCHAR(120), 
	latitude NUMERIC(10, 7), 
	longitude NUMERIC(10, 7), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(operator_id) REFERENCES operator (id), 
	FOREIGN KEY(local_authority_id) REFERENCES local_authority (id)
);

CREATE TABLE application (
	id SERIAL NOT NULL, 
	application_no VARCHAR(32) NOT NULL, 
	operator_id INTEGER NOT NULL, 
	property_id INTEGER NOT NULL, 
	local_authority_id INTEGER NOT NULL, 
	status VARCHAR(24) DEFAULT 'draft' NOT NULL, 
	assigned_officer_id INTEGER, 
	submitted_at TIMESTAMP WITH TIME ZONE, 
	status_changed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	decided_at TIMESTAMP WITH TIME ZONE, 
	decision_reason TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (application_no), 
	FOREIGN KEY(operator_id) REFERENCES operator (id), 
	FOREIGN KEY(property_id) REFERENCES property (id), 
	FOREIGN KEY(local_authority_id) REFERENCES local_authority (id), 
	FOREIGN KEY(assigned_officer_id) REFERENCES app_user (id)
);
CREATE INDEX ix_application_local_authority_id ON application (local_authority_id);
CREATE INDEX ix_application_status ON application (status);

CREATE TABLE application_classification (
	id SERIAL NOT NULL, 
	application_id INTEGER NOT NULL, 
	property_type_id INTEGER NOT NULL, 
	matched_rule_id INTEGER, 
	answered_rooms INTEGER NOT NULL, 
	answered_guests INTEGER NOT NULL, 
	answered_has_restaurant BOOLEAN NOT NULL, 
	reason_text TEXT NOT NULL, 
	classified_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (application_id), 
	FOREIGN KEY(application_id) REFERENCES application (id), 
	FOREIGN KEY(property_type_id) REFERENCES property_type (id), 
	FOREIGN KEY(matched_rule_id) REFERENCES classification_rule (id)
);

CREATE TABLE application_status_history (
	id SERIAL NOT NULL, 
	application_id INTEGER NOT NULL, 
	from_status VARCHAR(24), 
	to_status VARCHAR(24) NOT NULL, 
	changed_by_id INTEGER, 
	note TEXT, 
	changed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(application_id) REFERENCES application (id), 
	FOREIGN KEY(changed_by_id) REFERENCES app_user (id)
);

CREATE TABLE document_file (
	id SERIAL NOT NULL, 
	application_id INTEGER NOT NULL, 
	document_type_id INTEGER NOT NULL, 
	slot_no INTEGER DEFAULT '1' NOT NULL, 
	version_no INTEGER DEFAULT '1' NOT NULL, 
	is_current BOOLEAN DEFAULT 'true' NOT NULL, 
	stored_path VARCHAR(300) NOT NULL, 
	original_name VARCHAR(255) NOT NULL, 
	mime_type VARCHAR(100) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	status VARCHAR(24) DEFAULT 'uploaded' NOT NULL, 
	system_check_note TEXT, 
	uploaded_by_id INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_docfile_version UNIQUE (application_id, document_type_id, slot_no, version_no), 
	FOREIGN KEY(application_id) REFERENCES application (id), 
	FOREIGN KEY(document_type_id) REFERENCES document_type (id), 
	FOREIGN KEY(uploaded_by_id) REFERENCES app_user (id)
);

CREATE TABLE license (
	id SERIAL NOT NULL, 
	application_id INTEGER NOT NULL, 
	license_no VARCHAR(32) NOT NULL, 
	kind VARCHAR(20) NOT NULL, 
	property_type_id INTEGER NOT NULL, 
	issued_by_id INTEGER NOT NULL, 
	local_authority_id INTEGER NOT NULL, 
	fee_schedule_id INTEGER, 
	fee_amount NUMERIC(12, 2), 
	issued_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	valid_from DATE NOT NULL, 
	valid_until DATE, 
	is_revoked BOOLEAN DEFAULT 'false' NOT NULL, 
	issuer_signature_path VARCHAR(255), 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (application_id), 
	FOREIGN KEY(application_id) REFERENCES application (id), 
	UNIQUE (license_no), 
	FOREIGN KEY(property_type_id) REFERENCES property_type (id), 
	FOREIGN KEY(issued_by_id) REFERENCES app_user (id), 
	FOREIGN KEY(local_authority_id) REFERENCES local_authority (id), 
	FOREIGN KEY(fee_schedule_id) REFERENCES fee_schedule (id)
);

CREATE TABLE notification (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	application_id INTEGER, 
	title VARCHAR(200) NOT NULL, 
	body TEXT NOT NULL, 
	is_read BOOLEAN DEFAULT 'false' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES app_user (id), 
	FOREIGN KEY(application_id) REFERENCES application (id)
);
CREATE INDEX ix_notification_user_id ON notification (user_id);

CREATE TABLE document_review (
	id SERIAL NOT NULL, 
	document_file_id INTEGER NOT NULL, 
	reviewer_id INTEGER NOT NULL, 
	decision VARCHAR(24) NOT NULL, 
	comment TEXT, 
	reviewed_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_file_id) REFERENCES document_file (id), 
	FOREIGN KEY(reviewer_id) REFERENCES app_user (id)
);

