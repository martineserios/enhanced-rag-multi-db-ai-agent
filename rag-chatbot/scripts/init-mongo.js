// Initialize the database
db = db.getSiblingDB('ragchatbot');

// Create users collection
db.createCollection('users');
db.users.insertMany([
  {
    userId: 'user1',
    name: 'John Doe',
    email: 'john@example.com',
    profile: {
      age: 32,
      occupation: 'Software Engineer',
      location: 'San Francisco'
    },
    interests: ['programming', 'hiking', 'reading'],
    joinDate: new Date('2023-01-15')
  },
  {
    userId: 'user2',
    name: 'Jane Smith',
    email: 'jane@example.com',
    profile: {
      age: 28,
      occupation: 'Data Scientist',
      location: 'New York'
    },
    interests: ['data analysis', 'machine learning', 'yoga'],
    joinDate: new Date('2023-02-20')
  },
  {
    userId: 'user3',
    name: 'Robert Johnson',
    email: 'robert@example.com',
    profile: {
      age: 45,
      occupation: 'Product Manager',
      location: 'Chicago'
    },
    interests: ['product strategy', 'basketball', 'cooking'],
    joinDate: new Date('2023-03-10')
  }
]);

// Create documents collection (not for RAG, just as sample data)
db.createCollection('documents');
db.documents.insertMany([
  {
    documentId: 'doc1',
    title: 'Introduction to MongoDB',
    content: 'MongoDB is a document-oriented NoSQL database...',
    category: 'Database',
    tags: ['NoSQL', 'Database', 'MongoDB'],
    createdAt: new Date('2023-04-05')
  },
  {
    documentId: 'doc2',
    title: 'Machine Learning Basics',
    content: 'Machine learning is a subset of artificial intelligence...',
    category: 'AI',
    tags: ['Machine Learning', 'AI', 'Data Science'],
    createdAt: new Date('2023-04-12')
  },
  {
    documentId: 'doc3',
    title: 'Web Development with React',
    content: 'React is a JavaScript library for building user interfaces...',
    category: 'Web Development',
    tags: ['React', 'JavaScript', 'Frontend'],
    createdAt: new Date('2023-04-18')
  }
]);

// Create a settings collection
db.createCollection('settings');
db.settings.insertMany([
  {
    settingId: 'app_settings',
    theme: 'light',
    notifications: {
      email: true,
      push: false
    },
    defaultLanguage: 'English',
    updatedAt: new Date()
  },
  {
    settingId: 'system_settings',
    maintenance: false,
    version: '1.0.0',
    maxFileSize: 10 * 1024 * 1024, // 10MB
    allowedFileTypes: ['pdf', 'txt', 'doc', 'docx'],
    updatedAt: new Date()
  }
]);

// Create indexes
db.users.createIndex({ email: 1 }, { unique: true });
db.documents.createIndex({ title: 'text', content: 'text' });