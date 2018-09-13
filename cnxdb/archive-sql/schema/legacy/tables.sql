CREATE TABLE "persons" (
  "personid" text PRIMARY KEY,
  "honorific" text,
  "firstname" text,
  "othername" text,
  "surname" text,
  "lineage" text,
  "fullname" text,
  "email" text,
  "homepage" text,
  "comment" text,
  passwd bytea,
  groups text[]
);

CREATE TABLE moduleratings (
    module_ident integer REFERENCES modules (module_ident),
    totalrating integer,
    votes integer);
