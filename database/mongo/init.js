db = db.getSiblingDB("medicard");
const validator = {
  $jsonSchema: {
    bsonType: "object",
    required: ["version", "ciphertext", "nonce"],
    additionalProperties: false,
    properties: {
      _id: { bsonType: "objectId" },
      version: { bsonType: "int", enum: [1] },
      ciphertext: { bsonType: "string" },
      nonce: { bsonType: "string" }
    }
  }
};
if (!db.getCollectionNames().includes("audit_events")) {
  db.createCollection("audit_events", {
    validator: validator,
    validationLevel: "strict",
    validationAction: "error"
  });
} else {
  db.runCommand({
    collMod: "audit_events",
    validator: validator,
    validationLevel: "strict",
    validationAction: "error"
  });
}
