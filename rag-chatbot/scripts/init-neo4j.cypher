# filepath: scripts/init-neo4j.cypher
// Create sample procedures for the RAG system

// Document Upload Procedure
CREATE (p:Procedure {name: 'document_upload', created_at: datetime()});

CREATE (s1:Step {id: 'document_upload_step_0', order: 0, description: 'Select a document file from your computer', action: 'select_file'});
CREATE (s2:Step {id: 'document_upload_step_1', order: 1, description: 'Add an optional description for the document', action: 'add_description'});
CREATE (s3:Step {id: 'document_upload_step_2', order: 2, description: 'Click the Upload button to submit', action: 'click_upload'});
CREATE (s4:Step {id: 'document_upload_step_3', order: 3, description: 'Wait for the system to process the document', action: 'wait_processing'});
CREATE (s5:Step {id: 'document_upload_step_4', order: 4, description: 'Verify the document appears in the document list', action: 'verify_uploaded'});

CREATE (p)-[:HAS_STEP]->(s1);
CREATE (p)-[:HAS_STEP]->(s2);
CREATE (p)-[:HAS_STEP]->(s3);
CREATE (p)-[:HAS_STEP]->(s4);
CREATE (p)-[:HAS_STEP]->(s5);

CREATE (s1)-[:NEXT]->(s2);
CREATE (s2)-[:NEXT]->(s3);
CREATE (s3)-[:NEXT]->(s4);
CREATE (s4)-[:NEXT]->(s5);

// Database Query Procedure
CREATE (p2:Procedure {name: 'database_query', created_at: datetime()});

CREATE (q1:Step {id: 'database_query_step_0', order: 0, description: 'Enable the database options in the sidebar', action: 'enable_database'});
CREATE (q2:Step {id: 'database_query_step_1', order: 1, description: 'Type your question in the chat input', action: 'type_question'});
CREATE (q3:Step {id: 'database_query_step_2', order: 2, description: 'Send the message and wait for response', action: 'send_message'});
CREATE (q4:Step {id: 'database_query_step_3', order: 3, description: 'Examine the sources used in the response', action: 'check_sources'});

CREATE (p2)-[:HAS_STEP]->(q1);
CREATE (p2)-[:HAS_STEP]->(q2);
CREATE (p2)-[:HAS_STEP]->(q3);
CREATE (p2)-[:HAS_STEP]->(q4);

CREATE (q1)-[:NEXT]->(q2);
CREATE (q2)-[:NEXT]->(q3);
CREATE (q3)-[:NEXT]->(q4);

// Chat Process Procedure
CREATE (p3:Procedure {name: 'chat_process', created_at: datetime()});

CREATE (c1:Step {id: 'chat_process_step_0', order: 0, description: 'Select the LLM provider from the dropdown', action: 'select_provider'});
CREATE (c2:Step {id: 'chat_process_step_1', order: 1, description: 'Choose which memory types to enable', action: 'select_memory'});
CREATE (c3:Step {id: 'chat_process_step_2', order: 2, description: 'Type your question in the chat input', action: 'type_question'});
CREATE (c4:Step {id: 'chat_process_step_3', order: 3, description: 'Send the message and review the response', action: 'send_and_review'});

CREATE (p3)-[:HAS_STEP]->(c1);
CREATE (p3)-[:HAS_STEP]->(c2);
CREATE (p3)-[:HAS_STEP]->(c3);
CREATE (p3)-[:HAS_STEP]->(c4);

CREATE (c1)-[:NEXT]->(c2);
CREATE (c2)-[:NEXT]->(c3);
CREATE (c3)-[:NEXT]->(c4);

// Create indexes
CREATE INDEX ON :Procedure(name);
CREATE INDEX ON :Step(id);