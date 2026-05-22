// 1) 唯一约束（建议先建）
CREATE CONSTRAINT kp_node_id_unique IF NOT EXISTS
FOR (n:KnowledgePoint)
REQUIRE n.node_id IS UNIQUE;

// 2) 导入节点
LOAD CSV WITH HEADERS FROM 'file:///neo4j_nodes.csv' AS row
MERGE (n:KnowledgePoint {node_id: row["node_id:ID"]})
SET n.name = row["name"],
    n.level = toInteger(row["level:int"]),
    n.parent_id = CASE WHEN row["parent_id"] = "" THEN null ELSE row["parent_id"] END,
    n.course_name = row["course_name"];

// 3) 导入关系
LOAD CSV WITH HEADERS FROM 'file:///neo4j_relationships.csv' AS row
MATCH (p:KnowledgePoint {node_id: row[":START_ID"]})
MATCH (c:KnowledgePoint {node_id: row[":END_ID"]})
MERGE (p)-[r:CONTAINS]->(c)
SET r.order = toInteger(row["order:int"]);
