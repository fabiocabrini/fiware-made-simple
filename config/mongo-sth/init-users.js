// Run by the mongo-db-sth container only on the FIRST start (empty volume).
// To recreate the users, delete the fiware_mongo-db-sth-data volume.
//
// STH_MONGO_USER        used by STH-Comet; writes to the sth_<fiware-service> databases
// STH_MONGO_READER_USER read-only, for external access (Compass, Python, BI...)

const admin = db.getSiblingDB("admin");

admin.createUser({
  user: process.env.STH_MONGO_USER,
  pwd: process.env.STH_MONGO_PASSWORD,
  roles: [{ role: "readWriteAnyDatabase", db: "admin" }],
});

admin.createUser({
  user: process.env.STH_MONGO_READER_USER,
  pwd: process.env.STH_MONGO_READER_PASSWORD,
  roles: [{ role: "readAnyDatabase", db: "admin" }],
});
