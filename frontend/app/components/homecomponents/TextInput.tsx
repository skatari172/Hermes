import React from 'react';
import { View, TextInput, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface TextInputProps {
  value: string;
  onChangeText: (text: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  maxLength?: number;
}

export default function TextInputComponent({ 
  value, 
  onChangeText, 
  onSubmit, 
  placeholder = "Type a message..",
  maxLength = 500 
}: TextInputProps) {
  return (
    <View style={styles.textInputContainer}>
      <TextInput
        style={styles.textInput}
        placeholder={placeholder}
        value={value}
        onChangeText={onChangeText}
        multiline
        maxLength={maxLength}
      />
      <TouchableOpacity style={styles.submitButton} onPress={onSubmit}>
        <Ionicons name="send" size={20} color="#043263" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  textInputContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E5ECFF',
    borderRadius: 20,
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 16,
    paddingVertical: 12,
    minHeight: 40,
    maxHeight: 100,
  },
  textInput: {
    flex: 1,
    fontSize: 16,
    padding: 0,
    margin: 0,
    textAlignVertical: 'center',
  },
  submitButton: {
    padding: 4,
    marginLeft: 8,
  },
});
